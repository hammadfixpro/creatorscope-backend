"""Trending Videos (v2) — YouTube chart=mostPopular, NOT Google Trends.

GET /api/trending?region=PK&category_id=&max_results=25&refresh=0
Quota: videos.list chart=mostPopular = 1 unit + 1 batched channels.list
(1 unit) = 2 units per uncached call. Cached 3600s (settings TTL);
refresh=1 bypasses the trending-videos cache so an hourly refresh shows
new items. region=worldwide sends no regionCode. Demo mode returns the
demo dataset sorted by views, clearly labelled DEMO.
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from .. import service
from ..providers import demo as demo_mod
from ..providers.youtube import YouTubeProvider

router = APIRouter(prefix="/api/trending", tags=["trending"])

REGIONS = {"PK": "Pakistan", "US": "United States", "GB": "United Kingdom",
           "IN": "India", "worldwide": "Worldwide (no regionCode sent)"}
CATEGORIES = {"1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
              "15": "Pets & Animals", "17": "Sports", "19": "Travel & Events",
              "20": "Gaming", "22": "People & Blogs", "23": "Comedy",
              "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
              "27": "Education", "28": "Science & Technology"}

def _now():
    return datetime.now(timezone.utc).isoformat()

def _public(v):
    v = dict(v)
    v.pop("_keywords", None); v.pop("_days_ago", None)
    return v

@router.get("")
def trending(region: str = "PK", category_id: str = None, max_results: int = 25,
             refresh: int = 0, demo: int = None):
    region = region if region in REGIONS else "PK"
    max_results = min(max(1, max_results), 50)
    cat = category_id if category_id in CATEGORIES else None
    if service.use_demo(demo):
        ts = _now()
        items = sorted(demo_mod.all_videos(), key=lambda v: -v["views"])[:max_results]
        pub = [{**_public(v), "fetched_at": ts} for v in items]
        return {"items": pub, "total": len(items),
                "region": region, "region_name": REGIONS[region],
                "category_id": cat, "category_name": CATEGORIES.get(cat) if cat else None,
                "fetched_at": ts, "refresh": bool(refresh),
                "quota_cost_units": 0, "demo": True, "source": "demo"}
    try:
        yt = YouTubeProvider()
        videos = yt.trending_videos(region=None if region == "worldwide" else region,
                                    category_id=cat, max_results=max_results, refresh=bool(refresh))
        chan_ids = list({v["channel_id"] for v in videos if v.get("channel_id")})
        subs = {c["id"]: c["subscribers"] for c in yt.get_channels(chan_ids)} if chan_ids else {}
        ts = _now()
        for v in videos:
            v["channel_subscribers"] = subs.get(v["channel_id"])
        return {"items": [{**_public(v), "fetched_at": ts} for v in videos], "total": len(videos),
                "region": region, "region_name": REGIONS[region],
                "category_id": cat, "category_name": CATEGORIES.get(cat) if cat else None,
                "fetched_at": ts, "refresh": bool(refresh),
                "quota_cost_units": 2, "demo": False, "source": "youtube_api"}
    except Exception as e:
        ts = _now()
        items = sorted(demo_mod.all_videos(), key=lambda v: -v["views"])[:max_results]
        return {"items": [{**_public(v), "fetched_at": ts} for v in items], "total": len(items),
                "region": region, "region_name": REGIONS[region],
                "category_id": cat, "category_name": CATEGORIES.get(cat) if cat else None,
                "fetched_at": ts, "refresh": bool(refresh), "quota_cost_units": 0,
                "error": f"live trending unavailable, showing demo: {e}",
                "demo": True, "source": "demo"}
