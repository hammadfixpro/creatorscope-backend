import json, sqlite3, time
from pathlib import Path
from .config import settings

def get_conn():
    path = settings.database_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    schema = (Path(__file__).parent / "schema.sql").read_text()
    with get_conn() as conn:
        conn.executescript(schema)

def cache_get(key: str):
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT response, created_at, ttl_seconds FROM api_cache WHERE cache_key=?", (key,)).fetchone()
        if not row: return None
        if time.time() - row["created_at"] > row["ttl_seconds"]: return None
        return json.loads(row["response"])
    except Exception:
        return None

def cache_set(key: str, value, ttl: int):
    try:
        with get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO api_cache(cache_key,response,created_at,ttl_seconds) VALUES(?,?,?,?)",
                         (key, json.dumps(value), time.time(), ttl))
    except Exception:
        pass

def log_usage(endpoint: str, units: int):
    from datetime import datetime, timezone
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO usage_log(endpoint,quota_units,created_at) VALUES(?,?,?)",
                         (endpoint, units, datetime.now(timezone.utc).isoformat()))
    except Exception:
        pass

def usage_totals():
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT COALESCE(SUM(quota_units),0) AS u, COUNT(*) AS c FROM usage_log").fetchone()
        return {"quota_units_used": int(row["u"]), "calls": int(row["c"])}
    except Exception:
        return {"quota_units_used": 0, "calls": 0}
