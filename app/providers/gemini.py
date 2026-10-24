import httpx
from ..config import settings

def generate(prompt: str):
    """Call Gemini generateContent. Returns text or None if not configured/failed."""
    if not settings.gemini_api_key: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, headers={"x-goog-api-key": settings.gemini_api_key},
                            json={"contents": [{"parts": [{"text": prompt}]}]})
            r.raise_for_status()
            data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
