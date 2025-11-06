from flask import Blueprint

api_bp = Blueprint("api", __name__)

from . import auth, change_requests, audit  # noqa: F401,E402
