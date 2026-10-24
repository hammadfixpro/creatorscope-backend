import csv, io
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from .. import service
from ..providers import demo as demo_mod
from ..providers.youtube import YouTubeProvider
from ..sentiment import analyze_sentiment
from ..config import settings

router = APIRouter(prefix="/api/videos", tags=["videos"])

def _search_params(q, type, min_views, max_views, min_subs, max_subs, published_after, published_before, min_outlier, sort, language, region, demo_flag):
    items, source, is_demo = service.search_videos(demo_flag=demo_flag, q=q, type_=type, min_views=min_views, max_views=max_views,
        min_subs=min_subs, max_subs=max_subs, published_after=published_after, published_before=published_before,
        region=region, language=language)
    if min_outlier is not None:
        items = [v for v in items if (v.get("outlier_score") or 0) >= min_outlier]
    return service.sort_videos(items, sort), source, is_demo

@router.get("/search")
def search(q: str = "", type: str = "all", min_views: int = None, max_views: int = None,
           min_subs: int = None, max_subs: int = None, published_after: str = None, published_before: str = None,
           min_outlier: float = None, sort: str = "views", language: str = None, region: str = None,
           page: int = 1, page_size: int = 20, demo: int = None):
    items, source, is_demo = _search_params(q, type, min_views, max_views, min_subs, max_subs, published_after, published_before, min_outlier, sort, language, region, demo)
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start+page_size], "total": total, "page": page, "page_size": page_size, "source": source, "demo": is_demo}

@router.get("/export.csv")
def export_csv(q: str = "", type: str = "all", min_views: int = None, max_views: int = None,
           min_subs: int = None, max_subs: int = None, published_after: str = None, published_before: str = None,
           min_outlier: float = None, sort: str = "views", language: str = None, region: str = None, demo: int = None):
    items, source, is_demo = _search_params(q, type, min_views, max_views, min_subs, max_subs, published_after, published_before, min_outlier, sort, language, region, demo)
    buf = io.StringIO(); wr = csv.writer(buf)
    fields = ["id","title","channel_id","channel_title","published_at","views","likes","comments","duration_seconds","is_short","url","channel_subscribers","outlier_score","views_per_sub","views_per_hour"]
    wr.writerow(fields)
    for v in items: wr.writerow([v.get(f) for f in fields])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=creatorscope-videos.csv"})

@router.get("/{video_id}")
def detail(video_id: str, demo: int = None):
    v, is_demo = service.get_video(video_id, demo_flag=demo)
    if not v: return {"error": "video not found", "id": video_id}
    return {**v, "demo": is_demo, "source": "demo" if is_demo else "youtube_api"}

@router.get("/{video_id}/similar")
def similar(video_id: str, demo: int = None):
    v, is_demo = service.get_video(video_id, demo_flag=demo)
    if not v: return {"items": [], "error": "video not found"}
    if is_demo:
        pool = demo_mod.all_videos()
        kw = set((demo_mod.get_video(video_id) or {}).get("_keywords", "").split())
        scored = []
        for o in pool:
            if o["id"] == video_id: continue
            overlap = len(kw & set(o.get("_keywords","").split()))
            if overlap: scored.append((overlap, o))
        scored.sort(key=lambda x: -x[0])
        return {"items": service.enrich([o for _, o in scored[:10]], pool), "demo": True, "source": "demo"}
    words = " ".join(v["title"].split()[:5])
    items, source, dm = service.search_videos(q=words)
    return {"items": [i for i in items if i["id"] != video_id][:10], "demo": dm, "source": source}

@router.get("/{video_id}/comments")
def comments(video_id: str, demo: int = None):
    if service.use_demo(demo):
        items = demo_mod.COMMENTS
        return {"items": items, "sentiment": analyze_sentiment([c["text"] for c in items]), "demo": True, "source": "demo"}
    try:
        items = YouTubeProvider().comments(video_id)
        return {"items": items, "sentiment": analyze_sentiment([c["text"] for c in items]), "demo": False, "source": "youtube_api"}
    except Exception as e:
        return {"items": [], "sentiment": analyze_sentiment([]), "error": f"comments unavailable: {e}"}

@router.get("/{video_id}/transcript")
def transcript(video_id: str):
    return {"available": False,
            "reason": "YouTube Data API captions.list/download requires the channel owner's OAuth authorization; transcripts of other channels cannot be fetched through the official API.",
            "fallback": "Use the extension on the watch page where the user can open the transcript panel",
            "video_id": video_id}
