from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.has_role(*roles):
                flash("Você não tem permissão para acessar esta área.", "danger")
                return redirect(url_for("post_login_redirect"))
            return func(*args, **kwargs)

        return wrapper

    return decorator
