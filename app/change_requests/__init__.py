"""Change Requests Blueprint"""
from flask import Blueprint

cr_bp = Blueprint('cr', __name__)

# Import routes at the end to avoid circular imports
from . import routes  # noqa: E402, F401
