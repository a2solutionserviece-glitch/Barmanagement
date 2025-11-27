from functools import wraps
from flask import session, redirect, abort

# LOGIN REQUIRED
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# ROLE REQUIRED
def role_required(allowed_roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "role" not in session:
                return redirect("/login")

            if session["role"] not in allowed_roles:
                return abort(403)   # Forbidden
            return f(*args, **kwargs)
        return decorated
    return wrapper
