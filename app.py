from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import ensure_indexes
from routes.auth import bp as auth_bp
from routes.products import bp as products_bp
from routes.orders import bp as orders_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, origins=Config.CORS_ORIGINS or "*", supports_credentials=False)

    ensure_indexes()

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)

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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
