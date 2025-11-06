from functools import wraps
from flask import abort


def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Placeholder: integrate with flask-login current_user in real app
            # Here we assume a `g.current_user` or similar is set by auth
            from flask import g
            user = getattr(g, "current_user", None)
            if not user:
                abort(403)
            names = [r.name for r in getattr(user, "roles", [])]
            if role_name not in names:
                abort(403)
            return f(*args, **kwargs)

        return wrapper

    return decorator
