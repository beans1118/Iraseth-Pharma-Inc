from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db, ensure_indexes
from routes.auth import bp as auth_bp
from routes.products import bp as products_bp
from routes.orders import bp as orders_bp
from routes.inventory import bp as inventory_bp
from routes.users import bp as users_bp
from routes.logs import bp as logs_bp
from routes.backup import bp as backup_bp
from realtime import socketio
from utils.security import client_rate_limit


def create_app() -> Flask:
    Config.validate_production()

    app = Flask(__name__)
    app.config["COMPRESS_MIN_SIZE"] = Config.COMPRESS_MIN_SIZE
    app.config["COMPRESS_MIMETYPES"] = [
        "application/json",
        "text/html",
        "text/css",
        "application/javascript",
        "text/javascript",
    ]
    Compress(app)

    if Config.TRUST_PROXY_COUNT > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=Config.TRUST_PROXY_COUNT,
            x_proto=Config.TRUST_PROXY_COUNT,
            x_host=Config.TRUST_PROXY_COUNT,
        )

    CORS(
        app,
        origins=Config.CORS_ORIGINS or "*",
        supports_credentials=False,
    )

    ensure_indexes()

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(backup_bp)

    @app.before_request
    def phase2_rate_limits():
        """Protect the highest-risk API entry points without changing routes."""
        if request.method == "OPTIONS":
            return None

        path = request.path
        method = request.method

        if method == "POST" and path == "/api/auth/login":
            return client_rate_limit(
                "auth-login",
                Config.RATE_LIMIT_LOGIN_PER_MINUTE,
            )

        if method == "POST" and path == "/api/orders":
            return client_rate_limit(
                "public-order",
                Config.RATE_LIMIT_PUBLIC_ORDERS_PER_MINUTE,
            )

        if method == "POST" and path.startswith("/api/inventory/"):
            return client_rate_limit(
                "inventory-write",
                Config.RATE_LIMIT_INVENTORY_WRITES_PER_MINUTE,
            )

        if method == "POST" and path.startswith("/api/backup"):
            return client_rate_limit(
                "backup",
                Config.RATE_LIMIT_BACKUP_PER_MINUTE,
            )

        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        # This CSP is intentionally narrow so it hardens framing/base behavior
        # without changing the current frontend's scripts/styles.
        response.headers.setdefault(
            "Content-Security-Policy",
            "frame-ancestors 'none'; base-uri 'self'",
        )
        if Config.IS_PRODUCTION:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        if request.path.startswith("/api/auth"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/ready")
    def ready():
        try:
            db.command("ping")
            return jsonify({"status": "ready", "database": "ok"})
        except Exception:
            app.logger.exception("Readiness database check failed")
            return jsonify({"status": "not-ready", "database": "unavailable"}), 503

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception(e)
        return jsonify({"error": "Internal server error."}), 500

    socketio.init_app(
        app,
        cors_allowed_origins=Config.CORS_ORIGINS or "*",
    )
    from realtime import register_socket_handlers
    register_socket_handlers()

    return app


app = create_app()

if __name__ == "__main__":
    socketio.run(app, port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
