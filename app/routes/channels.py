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
    monetization = {
        "status": "unknown_via_api",
        "label": "Monetization: YouTube API se maloom nahi hota (sirf channel owner dekh sakta hai)",
        "explanation": "YouTube Data API v3 does NOT expose other channels' monetization status; it is owner-only analytics. No monetized yes/no is claimed here.",
        "signals_only": {"subscriber_count": ch.get("subscribers"), "total_views": ch.get("total_views"),
                         "video_count": ch.get("video_count"), "uploads_per_week": upw,
                         "avg_views_sample": round(mean(views), 1) if views else 0},
        "signals_note": "These are public eligibility signals only (e.g. the Partner Programme generally requires 1,000 subscribers), NOT proof of monetization: watch-time / Shorts-view criteria are private and cannot be checked via the API."}
    return {"id": ch["id"], "title": ch["title"], "monetization": monetization, "url": ch.get("url"),
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

def _similar_item(c, score, matched, avg_views, basis, sample_size, upw):
    return {"id": c["id"], "title": c["title"], "thumbnail_url": c.get("thumbnail_url"),
            "url": c.get("url"), "subscriber_count": c.get("subscribers"),
            "hidden_subscriber_count": c.get("hidden_subscriber_count", False),
            "total_views": c.get("total_views"), "video_count": c.get("video_count"),
            "created_at": c.get("created_at"), "avg_views": avg_views,
            "avg_views_basis": basis, "sample_size": sample_size,
            "uploads_per_week": upw, "similarity_score": score,
            "matched_keywords": matched, "topic_categories": c.get("topic_categories", [])}

@router.get("/{channel_id}/similar")
def similar(channel_id: str, demo: int = None, max_results: int = 10):
    from .. import similarity as sim
    from ..providers import demo as demo_mod
    ch, vids, is_demo = service.get_channel_with_videos(channel_id, demo_flag=demo)
    if not ch: return {"items": [], "error": "channel not found"}
    max_results = min(max(1, max_results), 20)
    seed_avg = sim.mean_views(vids) or sim.lifetime_avg_views(ch)
    if is_demo:
        seed_kw = sim.extract_keywords([ch.get("title", "")] + [v["title"] for v in vids] +
                                       [v.get("_keywords", "") for v in demo_mod.all_videos() if v["channel_id"] == channel_id])
        scored = []
        for c in demo_mod.all_channels():
            if c["id"] == channel_id: continue
            cvids = [v for v in demo_mod.all_videos() if v["channel_id"] == c["id"]]
            cand_kw = sim.extract_keywords([c["title"]] + [v["title"] for v in cvids] + [v.get("_keywords", "") for v in cvids])
            score, matched = sim.similarity_score(seed_kw, cand_kw, [], [], ch.get("subscribers"), c.get("subscribers"), seed_avg, sim.mean_views(cvids))
            if not matched: continue  # size closeness alone is not similarity
            scored.append(_similar_item(c, score, matched, sim.mean_views(cvids), "recent_sample", len(cvids), sim.uploads_per_week(cvids)))
        scored.sort(key=lambda x: -x["similarity_score"])
        return {"seed_channel": {"id": ch["id"], "title": ch["title"]}, "seed_keywords": seed_kw,
                "items": scored[:max_results], "total": len(scored),
                "score_formula": "0.45*keyword + 0.15*topic + 0.20*subscriber-log-closeness + 0.20*avg-views-log-closeness (see app/similarity.py)",
                "demo": True, "source": "demo"}
    # Live: keyword groups -> at most 3 channel searches (100 units each).
    from ..providers.youtube import YouTubeProvider
    seed_kw = sim.extract_keywords([ch.get("title", ""), ch.get("description", "")] + [v["title"] for v in vids])
    seed_topics = ch.get("topic_categories", [])
    try:
        yt = YouTubeProvider()
        queries = [" ".join(seed_kw[i:i + 3]) for i in range(0, min(len(seed_kw), 9), 3)][:3]
        if not queries: queries = [ch["title"]]
        cand_ids = []
        for q in queries:
            for cid in yt.search_channel_ids(q, max_results=25):
                if cid != channel_id and cid not in cand_ids: cand_ids.append(cid)
        cands = yt.get_channels(cand_ids) if cand_ids else []
        prelim = []
        for c in cands:
            score, matched = sim.similarity_score(seed_kw, sim.extract_keywords([c["title"], c.get("description", "")]),
                                                  seed_topics, c.get("topic_categories", []),
                                                  ch.get("subscribers"), c.get("subscribers"), seed_avg, sim.lifetime_avg_views(c))
            if not matched and not (set(seed_topics) & set(c.get("topic_categories", []))):
                continue  # size closeness alone is not similarity
            prelim.append((score, matched, c))
        prelim.sort(key=lambda x: -x[0])
        # Affordable recent sample: only the top candidates get a recent-video
        # fetch (3 units each); the rest keep their lifetime average, labelled.
        items, quota = [], len(queries) * 100 + 1
        for score, matched, c in prelim[:max_results]:
            avg, basis, sample, upw = sim.lifetime_avg_views(c), "lifetime", 0, 0.0
            try:
                recent = yt.channel_recent_videos(c["id"], max_results=10)
                if recent:
                    avg, basis, sample, upw = sim.mean_views(recent), "recent_sample", len(recent), sim.uploads_per_week(recent)
                    quota += 3
            except Exception:
                pass
            # Re-score with the recent-sample average; keywords/topics unchanged.
            score2, _ = sim.similarity_score(seed_kw, sim.extract_keywords([c["title"], c.get("description", "")]),
                                             seed_topics, c.get("topic_categories", []),
                                             ch.get("subscribers"), c.get("subscribers"), seed_avg, avg)
            items.append(_similar_item(c, score2, matched, avg, basis, sample, upw))
        items.sort(key=lambda x: -x["similarity_score"])
        return {"seed_channel": {"id": ch["id"], "title": ch["title"]}, "seed_keywords": seed_kw,
                "items": items, "total": len(items),
                "score_formula": "0.45*keyword + 0.15*topic + 0.20*subscriber-log-closeness + 0.20*avg-views-log-closeness (see app/similarity.py)",
                "quota_cost_units_estimate": quota, "quota_note": "Uncached worst case ~334 units; provider cache (3600s) makes repeats cost 0 fresh units.",
                "demo": False, "source": "youtube_api"}
    except Exception as e:
        return {"seed_channel": {"id": ch["id"], "title": ch["title"]}, "seed_keywords": seed_kw,
                "items": [], "error": f"similar channels unavailable: {e}", "demo": False, "source": "youtube_api"}
