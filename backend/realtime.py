"""
Authenticated Socket.IO real-time layer.

Rooms:
  inventory - any authenticated staff role
  logs      - superadmin/admin only
"""
from flask_socketio import SocketIO, emit, join_room

from config import Config

socketio = SocketIO(async_mode="threading")


def emit_stock_update(product: dict) -> None:
    socketio.emit("stock:update", product, room="inventory")


def emit_inventory_log(entry: dict) -> None:
    socketio.emit("log:inventory", entry, room="logs")


def emit_session_log(entry: dict) -> None:
    socketio.emit("log:session", entry, room="logs")


def register_socket_handlers() -> None:
    @socketio.on("join")
    def _on_join(data):
        data = data or {}
        room = data.get("room")
        if room not in ("inventory", "logs"):
            return {"ok": False, "error": "Unknown room."}

        if not Config.SOCKET_AUTH_REQUIRED:
            join_room(room)
            return {"ok": True, "room": room, "auth": "development-bypass"}

        # Import here to avoid a module-level circular dependency:
        # security.py emits session events through realtime.py.
        from utils.security import authenticate_token

        token = (data.get("token") or "").strip()
        allowed_roles = tuple(Config.ROLES)
        if room == "logs":
            allowed_roles = (Config.ROLE_SUPERADMIN, Config.ROLE_ADMIN)

        payload, error = authenticate_token(token, allowed_roles=allowed_roles)
        if error:
            emit("auth:error", {"error": error[0], "status": error[1]})
            return {"ok": False, "error": error[0], "status": error[1]}

        join_room(room)
        return {
            "ok": True,
            "room": room,
            "role": payload.get("role"),
        }
