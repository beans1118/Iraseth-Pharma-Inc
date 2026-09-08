"""
Real-time layer. One shared SocketIO instance, initialized against the Flask
app in app.py. Routes call the emit_* helpers here after writing to Mongo, so
every connected dashboard (Superadmin / Admin / Sub-admin) sees stock levels
and logs update live, without polling.

Rooms:
  "inventory" — anyone viewing the stock/inventory screen
  "logs"      — superadmin/admin viewing the audit log screen (session or
                inventory logs)
"""
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def emit_stock_update(product: dict) -> None:
    """Push the new quantity/status for one product to everyone watching inventory."""
    socketio.emit("stock:update", product, room="inventory")


def emit_inventory_log(entry: dict) -> None:
    """Push a new add/release log entry to superadmin + admin log viewers."""
    socketio.emit("log:inventory", entry, room="logs")


def emit_session_log(entry: dict) -> None:
    """Push a new login/logout log entry to superadmin + admin log viewers."""
    socketio.emit("log:session", entry, room="logs")


def register_socket_handlers() -> None:
    @socketio.on("join")
    def _on_join(data):
        from flask_socketio import join_room
        room = (data or {}).get("room")
        if room in ("inventory", "logs"):
            join_room(room)
