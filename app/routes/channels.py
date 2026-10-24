from fastapi import APIRouter
from statistics import mean
from .. import service
from ..scoring import median
router = APIRouter(prefix="/api/channels", tags=["channels"])

@router.get("/search")
def search(q: str = "", demo: int = None):
    chans, is_demo = service.search_channels(q, demo_flag=demo)
    items = [{"id": c["id"], "title": c["title"], "subscriber_count": c.get("subscribers"),
              "hidden_subscriber_count": c.get("hidden_subscriber_count", False),
              "total_views": c.get("total_views"), "video_count": c.get("video_count"),
              "created_at": c.get("created_at"), "thumbnail_url": c.get("thumbnail_url"),
              "url": c.get("url")} for c in chans]
    return {"items": items, "total": len(items), "demo": is_demo, "source": "demo" if is_demo else "youtube_api"}

@router.get("/{channel_id}")
def profile(channel_id: str, demo: int = None):
    ch, vids, is_demo = service.get_channel_with_videos(channel_id, demo_flag=demo)
    if not ch: return {"error": "channel not found", "id": channel_id}
    views = [v["views"] for v in vids]
    shorts = [v for v in vids if v["is_short"]]; longs = [v for v in vids if not v["is_short"]]
    def block(lst): return {"count": len(lst), "avg_views": round(mean([v["views"] for v in lst]), 1) if lst else 0}
    buckets = {"0-10k": 0, "10k-50k": 0, "50k-100k": 0, "100k-500k": 0, "500k+": 0}
    for x in views:
        if x < 10000: buckets["0-10k"] += 1
        elif x < 50000: buckets["10k-50k"] += 1
        elif x < 100000: buckets["50k-100k"] += 1
        elif x < 500000: buckets["100k-500k"] += 1
        else: buckets["500k+"] += 1
    outliers = sorted([v for v in vids if (v.get("outlier_score") or 0) >= 2], key=lambda v: -(v.get("outlier_score") or 0))
    # uploads/week from sample span
    upw = 0.0
    if len(vids) >= 2:
        dates = sorted(v["published_at"] for v in vids)
        from datetime import datetime
        try:
            span_days = max((datetime.fromisoformat(dates[-1].replace("Z","+00:00")) - datetime.fromisoformat(dates[0].replace("Z","+00:00"))).days, 1)
            upw = round(len(vids) / (span_days / 7.0), 2)
        except Exception: upw = 0.0
    return {"id": ch["id"], "title": ch["title"], "url": ch.get("url"),
      "thumbnail_url": ch.get("thumbnail_url"), "banner_url": ch.get("banner_url"),
      "subscriber_count": ch.get("subscribers"), "hidden_subscriber_count": ch.get("hidden_subscriber_count", False),
      "total_views": ch.get("total_views"), "video_count": ch.get("video_count"), "created_at": ch.get("created_at"),
      "avg_views": round(mean(views), 1) if views else 0, "median_views": median(views) if views else 0,
      "uploads_per_week": upw, "sample_size": len(vids),
      "shorts_vs_long": {"shorts": block(shorts), "long": block(longs)},
      "recent_uploads": sorted(vids, key=lambda v: v["published_at"], reverse=True),
      "outliers": outliers, "performance_distribution": buckets,
      "growth_history": [], "growth_note": "No historical snapshots collected yet for this channel. Use the Tracker (POST /api/tracker) so future snapshots build real growth history; growth is never fabricated.",
      "data_notes": {"statistics": "demo sample data" if is_demo else "official YouTube Data API v3",
                     "growth_history": "locally collected snapshots only", "revenue": "estimate only, not retrieved"},
      "demo": is_demo, "source": "demo" if is_demo else "youtube_api"}

@router.get("/{channel_id}/similar")
def similar(channel_id: str, demo: int = None):
    ch, vids, is_demo = service.get_channel_with_videos(channel_id, demo_flag=demo)
    if not ch: return {"items": [], "error": "channel not found"}
    # demo: channels whose videos share keywords; live: search channels by top video title words
    if is_demo:
        from ..providers import demo as demo_mod
        kw = set()
        for v in demo_mod.all_videos():
            if v["channel_id"] == channel_id: kw |= set(v.get("_keywords","").split())
        scored = []
        for c in demo_mod.all_channels():
            if c["id"] == channel_id: continue
            okw = set()
            for v in demo_mod.all_videos():
                if v["channel_id"] == c["id"]: okw |= set(v.get("_keywords","").split())
            ov = len(kw & okw)
            if ov: scored.append((ov, c))
        scored.sort(key=lambda x: -x[0])
        return {"items": [c for _, c in scored[:10]], "demo": True, "source": "demo"}
    q = " ".join(vids[0]["title"].split()[:4]) if vids else ch["title"]
    chans, dm = service.search_channels(q)
    return {"items": [c for c in chans if c["id"] != channel_id][:10], "demo": dm, "source": "demo" if dm else "youtube_api"}
