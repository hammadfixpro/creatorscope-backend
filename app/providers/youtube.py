"""YouTube Data API v3 provider. Keys ONLY from env (config.settings).
Quota costs (official): search.list = 100 units, videos/channels/playlistItems/commentThreads list = 1 unit per call.
Batching: list calls accept up to 50 ids. Responses cached in SQLite (api_cache) with TTL."""
import hashlib, json, re
import httpx
from ..config import settings
from .. import db

BASE = "https://www.googleapis.com/youtube/v3"
QUOTA = {"search": 100, "videos": 1, "channels": 1, "playlistItems": 1, "commentThreads": 1}

def _dur_to_seconds(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m: return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h*3600 + mi*60 + s

class YouTubeProvider:
    def __init__(self):
        self.key = settings.youtube_api_key
    @property
    def configured(self): return bool(self.key)

    def _get(self, endpoint, params, quota_key):
        cache_key = hashlib.sha256((endpoint + json.dumps(params, sort_keys=True)).encode()).hexdigest()
        cached = db.cache_get(cache_key)
        if cached is not None: return cached
        params = {**params, "key": self.key}
        with httpx.Client(timeout=20) as client:
            r = client.get(f"{BASE}/{endpoint}", params=params)
            r.raise_for_status()
            data = r.json()
        db.log_usage(endpoint, QUOTA.get(quota_key, 1))
        db.cache_set(cache_key, data, settings.cache_ttl_seconds)
        return data

    def test_connection(self):
        data = self._get("videos", {"part": "id", "chart": "mostPopular", "maxResults": 1}, "videos")
        return bool(data is not None)

    def search_video_ids(self, q, max_results=25, published_after=None, published_before=None, region=None, language=None, order="viewCount"):
        params = {"part": "snippet", "type": "video", "q": q or "", "maxResults": min(max_results, 50), "order": order}
        if published_after: params["publishedAfter"] = published_after
        if published_before: params["publishedBefore"] = published_before
        if region: params["regionCode"] = region
        if language: params["relevanceLanguage"] = language
        data = self._get("search", params, "search")
        return [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]

    def search_channel_ids(self, q, max_results=25):
        data = self._get("search", {"part": "snippet", "type": "channel", "q": q or "", "maxResults": min(max_results, 50)}, "search")
        return [it["id"]["channelId"] for it in data.get("items", []) if it.get("id", {}).get("channelId")]

    def get_videos(self, ids):
        out = []
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            if not batch: continue
            data = self._get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)}, "videos")
            for it in data.get("items", []):
                sn, st, cd = it.get("snippet", {}), it.get("statistics", {}), it.get("contentDetails", {})
                dur = _dur_to_seconds(cd.get("duration", ""))
                out.append({"id": it["id"], "title": sn.get("title", ""), "channel_id": sn.get("channelId", ""),
                    "channel_title": sn.get("channelTitle", ""), "thumbnail_url": (sn.get("thumbnails", {}).get("high", {}) or sn.get("thumbnails", {}).get("default", {})).get("url", ""),
                    "published_at": sn.get("publishedAt", ""), "views": int(st.get("viewCount", 0)),
                    "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0)),
                    "duration_seconds": dur, "is_short": dur <= 60,
                    "url": f"https://www.youtube.com/watch?v={it['id']}", "channel_subscribers": None,
                    "_keywords": (sn.get("title", "") + " " + " ".join(sn.get("tags", [])[:10])).lower()})
        return out

    def get_channels(self, ids):
        out = []
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            if not batch: continue
            data = self._get("channels", {"part": "snippet,statistics,brandingSettings", "id": ",".join(batch)}, "channels")
            for it in data.get("items", []):
                sn, st = it.get("snippet", {}), it.get("statistics", {})
                hidden = bool(st.get("hiddenSubscriberCount"))
                out.append({"id": it["id"], "title": sn.get("title", ""), "subscribers": None if hidden else int(st.get("subscriberCount", 0)),
                    "hidden_subscriber_count": hidden, "total_views": int(st.get("viewCount", 0)),
                    "video_count": int(st.get("videoCount", 0)), "created_at": sn.get("publishedAt", ""),
                    "thumbnail_url": (sn.get("thumbnails", {}).get("high", {}) or {}).get("url", ""),
                    "banner_url": ((it.get("brandingSettings", {}).get("image", {}) or {}).get("bannerExternalUrl")),
                    "url": f"https://www.youtube.com/channel/{it['id']}", "description": sn.get("description", "")[:500]})
        return out

    def channel_recent_videos(self, channel_id, max_results=15):
        """Uploads playlist -> recent video ids -> videos.list (for baselines)."""
        ch = self._get("channels", {"part": "contentDetails", "id": channel_id}, "channels")
        items = ch.get("items", [])
        if not items: return []
        uploads = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if not uploads: return []
        pl = self._get("playlistItems", {"part": "contentDetails", "playlistId": uploads, "maxResults": max_results}, "playlistItems")
        ids = [it["contentDetails"]["videoId"] for it in pl.get("items", [])]
        return self.get_videos(ids)

    def comments(self, video_id, max_results=25):
        data = self._get("commentThreads", {"part": "snippet", "videoId": video_id, "maxResults": max_results, "order": "relevance"}, "commentThreads")
        out = []
        for it in data.get("items", []):
            s = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            out.append({"author": s.get("authorDisplayName", ""), "text": s.get("textDisplay", ""),
                        "likes": int(s.get("likeCount", 0)), "published_at": s.get("publishedAt", "")})
        return out
