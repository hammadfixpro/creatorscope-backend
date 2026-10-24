import re
from datetime import datetime, timezone
from .config import settings
from .providers import demo
from .providers.youtube import YouTubeProvider
from .scoring import compute_outlier, median

def use_demo(demo_flag=None):
    if demo_flag in (1, "1", "true", True): return True
    return settings.demo_mode or not settings.youtube_configured

def _age_hours(published_at):
    try:
        dt = datetime.fromisoformat((published_at or "").replace("Z", "+00:00"))
        return max((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 1.0)
    except Exception:
        return None

def enrich(videos, pool=None):
    pool = pool if pool is not None else videos
    out = []
    for v in videos:
        v = dict(v)
        others = [o["views"] for o in pool if o.get("channel_id") == v.get("channel_id") and o.get("id") != v.get("id")]
        stats = compute_outlier(v.get("views", 0), others, v.get("channel_subscribers"))
        v.update(stats)
        ah = _age_hours(v.get("published_at"))
        v["views_per_hour"] = round(v["views"] / ah, 2) if ah else None
        v.pop("_keywords", None); v.pop("_days_ago", None)
        out.append(v)
    return out

def public_video(v): return v

def filter_videos(videos, q=None, type_="all", min_views=None, max_views=None, min_subs=None, max_subs=None,
                  published_after=None, published_before=None):
    out = []
    tokens = [t.lower() for t in re.split(r"\s+", q.strip()) if t] if q else []
    for v in videos:
        hay = (v.get("title","") + " " + v.get("_keywords","") + " " + v.get("channel_title","")).lower()
        if tokens and not all(t in hay for t in tokens): continue
        if type_ == "short" and not v.get("is_short"): continue
        if type_ == "long" and v.get("is_short"): continue
        if min_views is not None and v["views"] < min_views: continue
        if max_views is not None and v["views"] > max_views: continue
        subs = v.get("channel_subscribers")
        if min_subs is not None and (subs is None or subs < min_subs): continue
        if max_subs is not None and (subs is not None and subs > max_subs): continue
        if published_after and v.get("published_at","") < published_after: continue
        if published_before and v.get("published_at","") > published_before: continue
        out.append(v)
    return out

def sort_videos(videos, sort="views"):
    key = {"views": lambda v: v.get("views", 0),
           "outlier": lambda v: v.get("outlier_score") or 0,
           "recent": lambda v: v.get("published_at", ""),
           "vph": lambda v: v.get("views_per_hour") or 0}.get(sort, lambda v: v.get("views", 0))
    return sorted(videos, key=key, reverse=True)

def search_videos(demo_flag=None, **filters):
    """Returns (items_enriched, source, is_demo). Live path falls back to demo on API error."""
    if use_demo(demo_flag):
        pool = demo.all_videos()
        filtered = filter_videos(pool, **{k: filters.get(k) for k in ("q","type_","min_views","max_views","min_subs","max_subs","published_after","published_before") if k in filters or True})
        return enrich(filtered, pool), "demo", True
    try:
        yt = YouTubeProvider()
        ids = yt.search_video_ids(filters.get("q") or "", max_results=50,
                                  published_after=filters.get("published_after"), published_before=filters.get("published_before"),
                                  region=filters.get("region"), language=filters.get("language"))
        videos = yt.get_videos(ids)
        chan_ids = list({v["channel_id"] for v in videos if v.get("channel_id")})
        subs = {c["id"]: c["subscribers"] for c in yt.get_channels(chan_ids)}
        for v in videos: v["channel_subscribers"] = subs.get(v["channel_id"])
        filtered = filter_videos(videos, **{k: filters.get(k) for k in ("type_","min_views","max_views","min_subs","max_subs")})
        return enrich(filtered, videos), "youtube_api", False
    except Exception:
        pool = demo.all_videos()
        filtered = filter_videos(pool, q=filters.get("q"))
        return enrich(filtered, pool), "demo", True

def get_video(video_id, demo_flag=None):
    if use_demo(demo_flag):
        v = demo.get_video(video_id)
        if v: return enrich([v], demo.all_videos())[0], True
        return None, True
    try:
        yt = YouTubeProvider()
        vids = yt.get_videos([video_id])
        if not vids: return None, False
        v = vids[0]
        ch = yt.get_channels([v["channel_id"]])
        v["channel_subscribers"] = ch[0]["subscribers"] if ch else None
        recent = []
        try: recent = yt.channel_recent_videos(v["channel_id"])
        except Exception: recent = []
        pool = recent if recent else vids
        return enrich([v], pool)[0], False
    except Exception:
        v = demo.get_video(video_id)
        return (enrich([v], demo.all_videos())[0], True) if v else (None, True)

def get_channel_with_videos(channel_id, demo_flag=None):
    if use_demo(demo_flag):
        ch = demo.get_channel(channel_id)
        if not ch: return None, [], True
        vids = [v for v in demo.all_videos() if v["channel_id"] == channel_id]
        return ch, enrich(vids, demo.all_videos()), True
    try:
        yt = YouTubeProvider()
        chs = yt.get_channels([channel_id])
        if not chs: return None, [], False
        recent = yt.channel_recent_videos(channel_id, max_results=25)
        chan_subs = chs[0]["subscribers"]
        for v in recent: v["channel_subscribers"] = chan_subs
        return chs[0], enrich(recent, recent), False
    except Exception:
        ch = demo.get_channel(channel_id)
        if not ch: return None, [], True
        vids = [v for v in demo.all_videos() if v["channel_id"] == channel_id]
        return ch, enrich(vids, demo.all_videos()), True

def search_channels(q=None, demo_flag=None):
    if use_demo(demo_flag):
        chans = demo.all_channels()
        if q:
            toks = q.lower().split()
            chans = [c for c in chans if all(t in c["title"].lower() for t in toks)]
        return chans, True
    try:
        yt = YouTubeProvider()
        ids = yt.search_channel_ids(q or "")
        return yt.get_channels(ids), False
    except Exception:
        return demo.all_channels(), True
