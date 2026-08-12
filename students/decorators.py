from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if request.user.role not in roles:
                return redirect("dashboard")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator

