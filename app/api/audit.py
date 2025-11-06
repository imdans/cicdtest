from flask import jsonify
from . import api_bp


@api_bp.route("/audit/ping")
def audit_ping():
    return jsonify({"ok": True, "service": "audit"})
