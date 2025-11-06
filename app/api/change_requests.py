from flask import jsonify
from . import api_bp


@api_bp.route("/change-requests/ping")
def change_requests_ping():
    return jsonify({"ok": True, "service": "change_requests"})
