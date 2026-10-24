CREATE TABLE IF NOT EXISTS collections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'general',
  notes TEXT DEFAULT '', tags TEXT DEFAULT '[]',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS collection_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
  item_type TEXT NOT NULL, item_id TEXT NOT NULL,
  title TEXT DEFAULT '', url TEXT DEFAULT '', thumbnail_url TEXT DEFAULT '',
  notes TEXT DEFAULT '', tags TEXT DEFAULT '[]', meta TEXT DEFAULT '{}',
  created_at TEXT NOT NULL,
  UNIQUE(collection_id, item_type, item_id)
);
CREATE TABLE IF NOT EXISTS tracked_channels (
  channel_id TEXT PRIMARY KEY, title TEXT DEFAULT '',
  added_at TEXT NOT NULL, last_snapshot_at TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel_id TEXT NOT NULL, taken_at TEXT NOT NULL,
  subscriber_count INTEGER, total_views INTEGER, video_count INTEGER,
  raw TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS api_cache (
  cache_key TEXT PRIMARY KEY, response TEXT NOT NULL, created_at REAL NOT NULL, ttl_seconds INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  endpoint TEXT NOT NULL, quota_units INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
