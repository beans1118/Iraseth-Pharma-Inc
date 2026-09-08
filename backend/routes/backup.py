"""
Backups. Superadmin-only. Snapshots every collection that matters
(products, orders, users minus password hashes, sessions, inventory_logs)
into one timestamped JSON file under backend/<Config.BACKUP_DIR>/, so the
whole system state can be restored if something goes wrong.

This is triggered manually here (POST /run). To run it automatically, add a
cron job / scheduled task that calls this endpoint on a schedule (e.g. daily
at 2am) — see PROPOSAL.md for the recommended schedule.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

from flask import Blueprint, jsonify, send_from_directory

from config import Config
from extensions import db
from utils.security import require_role

bp = Blueprint("backup", __name__, url_prefix="/api/backup")

BACKUP_DIR = Path(__file__).resolve().parent.parent / Config.BACKUP_DIR


def _json_default(o):
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)


@bp.post("/run")
@require_role("superadmin")
def run_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def strip(docs):
        out = []
        for d in docs:
            d = dict(d)
            d["_id"] = str(d.get("_id", ""))
            d.pop("password_hash", None)
            out.append(d)
        return out

    snapshot = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "products": strip(db.products.find()),
        "orders": strip(db.orders.find()),
        "users": strip(db.users.find()),
        "sessions": strip(db.sessions.find()),
        "inventory_logs": strip(db.inventory_logs.find()),
    }

    filename = f"backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    path = BACKUP_DIR / filename
    path.write_text(json.dumps(snapshot, indent=2, default=_json_default))

    record = {
        "filename": filename,
        "created_at": snapshot["created_at"],
        "counts": {k: len(v) for k, v in snapshot.items() if isinstance(v, list)},
    }
    db.backups.insert_one(dict(record))
    record.pop("_id", None)
    return jsonify(record), 201


@bp.get("")
@require_role("superadmin")
def list_backups():
    rows = []
    for b in db.backups.find().sort("created_at", -1):
        b = dict(b)
        b.pop("_id", None)
        rows.append(b)
    return jsonify(rows)


@bp.get("/<filename>/download")
@require_role("superadmin")
def download_backup(filename):
    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)
