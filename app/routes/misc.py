from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..config import settings, APP_NAME
from .. import db, service
from ..scoring import revenue_estimate
from ..providers.youtube import YouTubeProvider
from ..providers import gemini
router = APIRouter(prefix="/api", tags=["misc"])

@router.get("/settings/status")
def status():
    return {"youtube_configured": settings.youtube_configured, "gemini_configured": settings.gemini_configured,
            "demo_mode": settings.demo_mode, "backend_url": settings.backend_url,
            "cache_ttl_seconds": settings.cache_ttl_seconds, "usage": db.usage_totals()}

@router.post("/settings/test-youtube")
def test_youtube():
    if not settings.youtube_configured:
        return {"ok": False, "message": "No YouTube API key configured. Get a free key: 1) console.cloud.google.com -> create project, 2) enable 'YouTube Data API v3', 3) create an API key, 4) put YOUTUBE_API_KEY=<key> in backend/.env and restart. Until then the app runs in clearly-labeled demo mode."}
    try:
        ok = YouTubeProvider().test_connection()
        return {"ok": bool(ok), "message": "YouTube Data API v3 connection OK (cheap videos.list chart call, 1 quota unit)." if ok else "YouTube API returned no data."}
    except Exception as e:
        return {"ok": False, "message": f"YouTube API call failed: {e}. Check the key, that YouTube Data API v3 is enabled, and remaining quota (10,000 units/day default; search costs 100)."}

@router.get("/usage")
def usage():
    return db.usage_totals()

class RevenueIn(BaseModel):
    category: str = "general"; country: str = "US"; format: str = "long"
    rpm_low: float = 5.0; rpm_mid: float = 12.0; rpm_high: float = 25.0; monthly_views: float = 100000

@router.post("/revenue/estimate")
def revenue(body: RevenueIn):
    est = revenue_estimate(body.monthly_views, body.rpm_low, body.rpm_mid, body.rpm_high)
    return {**est, "category": body.category, "country": body.country, "format": body.format,
            "monthly_views": body.monthly_views,
            "disclaimer": "Estimate only, based on YOUR editable RPM assumptions. Actual RPM/revenue is private channel-owner analytics data and cannot be retrieved for competitors; this is not verified earnings and not a guarantee."}

class ChatIn(BaseModel):
    message: str; context: Optional[dict] = None

@router.post("/ai/chat")
def chat(body: ChatIn):
    msg = body.message or ""
    # Grounding: retrieve real data from our own search first.
    import re
    stop = set("find me the a for with and show youtube niches niche channels channel videos video please".split())
    words = [w for w in re.findall(r"[a-zA-Z0-9]+", msg.lower()) if w not in stop]
    query = " ".join(words[:3])
    items, source, is_demo = service.search_videos(q=query) if query else ([], "demo", service.use_demo())
    items = service.sort_videos(items, "outlier")[:5]
    sources = [{"type": "video", "id": v["id"], "title": v["title"], "url": v["url"],
                "views": v["views"], "outlier_score": v.get("outlier_score")} for v in items]
    if not items:
        answer = ("I could not retrieve matching data from the configured source, so I will not invent statistics. "
                  "Try a simpler topic keyword (for example 'finance', 'history' or 'ai tools'), or add a YouTube API key in Settings to search live data.")
        return {"answer": answer, "sources": [], "demo": is_demo}
    lines = [f"Based on {'demo sample' if is_demo else 'live YouTube API'} data retrieved just now for '{query}':"]
    for v in items:
        lines.append(f"- '{v['title']}' by {v['channel_title']}: {v['views']:,} views, outlier score {v.get('outlier_score')} "
                     f"(baseline {v.get('baseline_views')}, sample {v.get('sample_size')}, confidence {v.get('confidence')}).")
    lines.append("These numbers come only from the retrieved items listed in sources; no other statistics are claimed.")
    grounded = "\n".join(lines)
    if settings.gemini_configured:
        text = gemini.generate("Answer the user using ONLY this retrieved data. Do not add any statistics not present.\n\nUser: " + msg + "\n\nData:\n" + grounded)
        if text: return {"answer": text, "sources": sources, "demo": is_demo, "model": settings.gemini_model}
    return {"answer": grounded, "sources": sources, "demo": is_demo}
