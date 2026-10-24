from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter
from statistics import mean
from .. import service
from ..scoring import median, opportunity_score, revenue_estimate
router = APIRouter(prefix="/api", tags=["niches"])

TOPICS = [
 ("Personal Finance & Investing", ("finance","investing","budget","money","debt","funds")),
 ("AI Tools & Automation", ("ai","automation","agent","agents","software")),
 ("History & Forgotten Stories", ("history","ancient","medieval","roman","army")),
 ("Fitness & Home Workout", ("fitness","workout","posture","mobility","health")),
 ("Quick Cooking & Recipes", ("cooking","recipes","rice","breakfast","dinner","food","kitchen")),
 ("Tech & Gadget Reviews", ("tech","gadgets","earbuds","laptop","phone")),
 ("Budget Travel", ("travel","trip","country","mountains")),
 ("Pet Care", ("dog","pets","pet")),
 ("Gaming Lore", ("gaming","lore","boss","game")),
 ("Study & Productivity", ("study","focus","productivity","pomodoro","exam")),
]
RPM = {name: (8, 15, 28) for name, _ in TOPICS}

def _topic(video):
    hay = (video.get("title","") + " " + video.get("_keywords","")).lower()
    # demo videos carry keywords; live titles also work
    for name, kws in TOPICS:
        if any(k in hay for k in kws): return name
    return video.get("channel_title") or "General"

@router.get("/niches/finder")
def finder(q: str = "", region: str = None, language: str = None, format: str = "all",
           min_subs: int = None, max_subs: int = None, min_views: int = None, max_views: int = None,
           min_vps_ratio: float = None, min_outlier: float = None, competition: str = None,
           min_uploads_per_week: float = None, published_within_days: int = None,
           sort: str = "opportunity", demo: int = None):
    from ..providers import demo as demo_mod
    is_demo = service.use_demo(demo)
    if is_demo:
        pool = demo_mod.all_videos()
        items = service.enrich(service.filter_videos(pool, q=q, type_=format if format in ("short","long") else "all",
            min_views=min_views, max_views=max_views, min_subs=min_subs, max_subs=max_subs), pool)
        raw_pool = pool
    else:
        items, source, dm = service.search_videos(q=q or "a", type_=format if format in ("short","long") else "all")
        is_demo = dm; raw_pool = items
    if published_within_days:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=published_within_days)).isoformat()
        items = [v for v in items if v.get("published_at","") >= cutoff[:10]]
    if min_outlier is not None:
        items = [v for v in items if (v.get("outlier_score") or 0) >= min_outlier]
    if min_vps_ratio is not None:
        items = [v for v in items if (v.get("views_per_sub") or 0) >= min_vps_ratio]
    groups = defaultdict(list)
    for v in items:
        # need topic from raw (keywords stripped by enrich) -> recompute from title/channel
        groups[_topic(v)].append(v)
    niches = []
    for name, vids in groups.items():
        chans = {}
        for v in vids: chans[v["channel_id"]] = {"id": v["channel_id"], "title": v["channel_title"], "subscribers": v.get("channel_subscribers")}
        n_ch = len(chans)
        comp = "low" if n_ch <= 1 else ("medium" if n_ch <= 3 else "high")
        if competition and comp != competition: continue
        avg_v = mean([v["views"] for v in vids]) if vids else 0
        avg_o = mean([v.get("outlier_score") or 1 for v in vids]) if vids else 1
        opp = opportunity_score(avg_v, avg_o, comp)
        rl, rm, rh = RPM.get(name, (6, 12, 22))
        monthly = avg_v * 4  # assumption: ~1 upload/week at average views
        rev = revenue_estimate(monthly, rl, rm, rh)
        niches.append({"name": name, "representative_channels": list(chans.values()),
          "example_videos": sorted(vids, key=lambda x: -x["views"])[:3],
          "avg_views": round(avg_v, 1), "median_views": median([v["views"] for v in vids]),
          "competition_level": comp, "opportunity_score": opp,
          "revenue_estimate": {**rev, "assumptions": f"RPM low/mid/high = ${rl}/${rm}/${rh} (editable assumption, category default); monthly views assumed = avg video views x 4 uploads/month. Estimates only -- actual RPM is private owner analytics."},
          "confidence": "medium" if len(vids) >= 3 else "low", "sample_size": len(vids),
          "source": "demo" if is_demo else "youtube_api", "demo": is_demo,
          "updated_at": datetime.now(timezone.utc).isoformat()})
    key = {"opportunity": lambda n: n["opportunity_score"], "views": lambda n: n["avg_views"],
           "outlier": lambda n: mean([v.get("outlier_score") or 0 for v in groups[n["name"]]])}.get(sort, lambda n: n["opportunity_score"])
    niches.sort(key=key, reverse=True)
    return {"items": niches, "total": len(niches), "demo": is_demo,
            "note": "Demo seed niches -- clearly labeled sample data, not live research." if is_demo else "Derived live by grouping searched videos into topic clusters.",
            "opportunity_formula": "0.45*demand(log avg views) + 0.35*outlier component + 0.20*competition component (see app/scoring.py)"}

@router.get("/outliers")
def outliers(q: str = "", min_outlier: float = None, page: int = 1, page_size: int = 20, demo: int = None):
    items, source, is_demo = service.search_videos(demo_flag=demo, q=q)
    items = service.sort_videos(items, "outlier")
    if min_outlier is not None: items = [v for v in items if (v.get("outlier_score") or 0) >= min_outlier]
    total = len(items); start = (page-1)*page_size
    return {"items": items[start:start+page_size], "total": total, "page": page, "page_size": page_size, "demo": is_demo, "source": source,
            "formula": "outlier_score = video views / median views of other recent videos from the same channel"}

@router.get("/trends")
def trends(keyword: str = "", region: str = "US", demo: int = None):
    kw = keyword or "faceless youtube"
    items, source, is_demo = service.search_videos(demo_flag=demo, q=kw)
    related = list({v["title"] for v in items[:8]})
    return {"keyword": kw, "region": region,
            "google_trends_url": f"https://trends.google.com/trends/explore?q={kw.replace(' ', '%20')}&geo={region}",
            "related_searches": related, "related_source": "YouTube search result titles (labeled source; not Google Trends data)",
            "limitations": "Google Trends has no universally available public programmatic API (restricted Alpha). Use the Google Trends link for official trend curves; related_searches here come from YouTube results only.",
            "demo": is_demo, "source": source}
