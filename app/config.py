import os
from pathlib import Path

def _load_dotenv():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

class Settings:
    @property
    def youtube_api_key(self): return os.environ.get("YOUTUBE_API_KEY", "")
    @property
    def gemini_api_key(self): return os.environ.get("GEMINI_API_KEY", "")
    @property
    def gemini_model(self): return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    @property
    def backend_url(self): return os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
    @property
    def cache_ttl_seconds(self): return int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
    @property
    def database_path(self):
        p = os.environ.get("DATABASE_PATH", "data/creatorscope.db")
        path = Path(p)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent / path
        return path
    @property
    def demo_mode(self):
        forced = os.environ.get("DEMO_MODE", "")
        if forced in ("1", "true", "True"):
            return True
        return not bool(self.youtube_api_key)
    @property
    def youtube_configured(self): return bool(self.youtube_api_key)
    @property
    def gemini_configured(self): return bool(self.gemini_api_key)

settings = Settings()
APP_NAME = os.environ.get("APP_NAME", "CreatorScope AI")
