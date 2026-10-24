import json
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from .. import db, service
router = APIRouter(prefix="/api/tracker", tags=["tracker"])

class TrackIn(BaseModel):
    channel_id: str

@router.post("")
def add(body: TrackIn):
    ch, vids, is_demo = service.get_channel_with_videos(body.channel_id)
    title = ch["title"] if ch else body.channel_id
    with db.get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO tracked_channels(channel_id,title,added_at) VALUES(?,?,?)",
                     (body.channel_id, title, datetime.now(timezone.utc).isoformat()))
    snap = snapshot(body.channel_id)
    return {"ok": True, "channel_id": body.channel_id, "title": title, "snapshot": snap}

@router.get("")
def list_tracked():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM tracked_channels ORDER BY added_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows),
            "note": "Snapshots are periodic, not real-time."}

@router.post("/{channel_id}/snapshot")
def snapshot(channel_id: str):
    ch, vids, is_demo = service.get_channel_with_videos(channel_id)
    if not ch: return {"error": "channel not found"}
    taken = datetime.now(timezone.utc).isoformat()
    with db.get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO tracked_channels(channel_id,title,added_at) VALUES(?,?,?)", (channel_id, ch["title"], taken))
        cur = conn.execute("INSERT INTO snapshots(channel_id,taken_at,subscriber_count,total_views,video_count,raw) VALUES(?,?,?,?,?,?)",
            (channel_id, taken, ch.get("subscribers"), ch.get("total_views"), ch.get("video_count"), json.dumps({"demo": is_demo})))
        conn.execute("UPDATE tracked_channels SET last_snapshot_at=? WHERE channel_id=?", (taken, channel_id))
        row = conn.execute("SELECT * FROM snapshots WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@router.get("/{channel_id}/snapshots")
def snapshots(channel_id: str):
    with db.get_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM snapshots WHERE channel_id=? ORDER BY taken_at ASC", (channel_id,)).fetchall()]
    deltas = []
    for prev, cur in zip(rows, rows[1:]):
        def d(k): return (cur.get(k) or 0) - (prev.get(k) or 0) if cur.get(k) is not None and prev.get(k) is not None else None
        deltas.append({"from": prev["taken_at"], "to": cur["taken_at"], "views_gained": d("total_views"),
                       "subs_gained": d("subscriber_count"), "new_videos": d("video_count")})
    return {"snapshots": rows, "deltas": deltas,
            "note": "Growth is computed only between locally collected snapshots; nothing is fabricated when snapshots are missing."}
