import json
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from .. import db
router = APIRouter(prefix="/api/collections", tags=["collections"])

def now(): return datetime.now(timezone.utc).isoformat()

class CollectionIn(BaseModel):
    name: str; kind: str = "general"; notes: str = ""; tags: List[str] = []
class ItemIn(BaseModel):
    item_type: str; item_id: str; title: str = ""; url: str = ""; thumbnail_url: str = ""
    notes: str = ""; tags: List[str] = []; meta: dict = {}

def _row(r): return {"id": r["id"], "name": r["name"], "kind": r["kind"], "notes": r["notes"],
                     "tags": json.loads(r["tags"] or "[]"), "created_at": r["created_at"], "updated_at": r["updated_at"]}
def _item(r): return {"id": r["id"], "collection_id": r["collection_id"], "item_type": r["item_type"], "item_id": r["item_id"],
                      "title": r["title"], "url": r["url"], "thumbnail_url": r["thumbnail_url"], "notes": r["notes"],
                      "tags": json.loads(r["tags"] or "[]"), "meta": json.loads(r["meta"] or "{}"), "created_at": r["created_at"]}

@router.post("")
def create(body: CollectionIn):
    with db.get_conn() as conn:
        cur = conn.execute("INSERT INTO collections(name,kind,notes,tags,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                           (body.name, body.kind, body.notes, json.dumps(body.tags), now(), now()))
        row = conn.execute("SELECT * FROM collections WHERE id=?", (cur.lastrowid,)).fetchone()
    return _row(row)

@router.get("")
def list_collections():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM collections ORDER BY created_at DESC").fetchall()
    return {"items": [_row(r) for r in rows], "total": len(rows)}

@router.post("/{collection_id}/items")
def add_item(collection_id: int, body: ItemIn):
    with db.get_conn() as conn:
        if not conn.execute("SELECT id FROM collections WHERE id=?", (collection_id,)).fetchone():
            return {"error": "collection not found"}
        cur = conn.execute("INSERT OR REPLACE INTO collection_items(collection_id,item_type,item_id,title,url,thumbnail_url,notes,tags,meta,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (collection_id, body.item_type, body.item_id, body.title, body.url, body.thumbnail_url, body.notes, json.dumps(body.tags), json.dumps(body.meta), now()))
        row = conn.execute("SELECT * FROM collection_items WHERE id=?", (cur.lastrowid,)).fetchone()
    return _item(row)

@router.get("/{collection_id}/items")
def get_items(collection_id: int):
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM collection_items WHERE collection_id=? ORDER BY created_at DESC", (collection_id,)).fetchall()
    return {"items": [_item(r) for r in rows], "total": len(rows)}

@router.delete("/{collection_id}/items/{item_pk}")
def delete_item(collection_id: int, item_pk: int):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM collection_items WHERE collection_id=? AND (id=? OR item_id=?)", (collection_id, item_pk, str(item_pk)))
    return {"ok": True}

@router.delete("/{collection_id}")
def delete_collection(collection_id: int):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM collection_items WHERE collection_id=?", (collection_id,))
        conn.execute("DELETE FROM collections WHERE id=?", (collection_id,))
    return {"ok": True}
