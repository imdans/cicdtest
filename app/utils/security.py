from itsdangerous import URLSafeTimedSerializer
from flask import current_app


def make_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
