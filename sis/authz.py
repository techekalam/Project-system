from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


ROLE_ADMIN = "Administrators"
ROLE_REGISTRY = "Registry"
ROLE_FINANCE = "Finance"
ROLE_LECTURER = "Lecturer"
ROLE_STUDENT = "Student"


def user_in_group(user, group_name: str) -> bool:
    if not user or isinstance(user, AnonymousUser):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name=group_name).exists()


def require_any_group(*group_names: str):
    def decorator(view: Callable[[HttpRequest, ...], HttpResponse]):
        def _wrapped(request: HttpRequest, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('login')}?next={request.path}")
            if request.user.is_superuser:
                return view(request, *args, **kwargs)
            if any(user_in_group(request.user, g) for g in group_names):
                return view(request, *args, **kwargs)
            return redirect("sis:home")

        return _wrapped

    return decorator

