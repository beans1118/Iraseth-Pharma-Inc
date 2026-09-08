from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import ensure_indexes
from routes.auth import bp as auth_bp
from routes.products import bp as products_bp
from routes.orders import bp as orders_bp
from routes.inventory import bp as inventory_bp
from routes.users import bp as users_bp
from routes.logs import bp as logs_bp
from routes.backup import bp as backup_bp
from realtime import socketio


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, origins=Config.CORS_ORIGINS or "*", supports_credentials=False)

    ensure_indexes()

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(backup_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception(e)
        return jsonify({"error": "Internal server error."}), 500

    socketio.init_app(app)
    from realtime import register_socket_handlers
    register_socket_handlers()

    return app


app = create_app()

if __name__ == "__main__":
    # socketio.run (not app.run) so the WebSocket layer for real-time
    # inventory/log updates actually starts.
    socketio.run(app, port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
