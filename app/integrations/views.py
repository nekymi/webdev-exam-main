import hmac

from flask import current_app, jsonify, request

from app.integrations import integrations_bp
from app.services.catalog_sync_service import run_api_stub_import


@integrations_bp.route("/1c/import", methods=["POST"])
def onec_import():
    """Закрытый endpoint для импорта из 1С (пока заглушка). Требуется API key в заголовке X-API-Key."""
    api_key = request.headers.get("X-API-Key")
    expected = current_app.config.get("INTEGRATION_API_KEY")
    if not expected or not api_key or not hmac.compare_digest(api_key, expected):
        return jsonify({"error": "Unauthorized", "message": "Invalid or missing API key"}), 401

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Bad request", "message": "JSON body required"}), 400

    try:
        log, result = run_api_stub_import(data)
        return jsonify({
            "ok": True,
            "created": result.created_count,
            "updated": result.updated_count,
            "errors": result.error_count,
            "log_id": log.id,
            "details": result.errors[:50],
        }), 200
    except Exception:
        current_app.logger.exception("1c import failed")
        return jsonify({"error": "Import failed", "message": "Internal import error"}), 500
