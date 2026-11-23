from rest_framework.permissions import BasePermission

from .models import RoleCode


def manageable_user_roles(user):
    """Роли сотрудников, которыми можно управлять из рабочего кабинета."""
    if user.is_superuser and user.role == RoleCode.ADMINISTRATOR:
        return set(RoleCode.values)
    if user.role == RoleCode.DIRECTOR:
        return {RoleCode.PROJECT_MANAGER, RoleCode.FOREMAN, RoleCode.WORKER}
    if user.role == RoleCode.PROJECT_MANAGER:
        return {RoleCode.FOREMAN, RoleCode.WORKER}
    return set()


def can_edit_user(actor, target):
    """Единая проверка для API и отображения доступных действий в интерфейсе."""
    if actor.is_superuser and actor.role == RoleCode.ADMINISTRATOR:
        return True
    return (target.pk != actor.pk and not target.is_superuser and not target.is_staff
            and target.role in manageable_user_roles(actor))


class CanManageUsers(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active
                    and manageable_user_roles(user))

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser and user.role == RoleCode.ADMINISTRATOR:
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return can_edit_user(user, obj)


class IsDirectorOrProjectManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role
            in [
                RoleCode.ADMINISTRATOR,
                RoleCode.DIRECTOR,
                RoleCode.PROJECT_MANAGER,
            ]
        )


class IsAdminScope(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in [
            RoleCode.ADMINISTRATOR,
            RoleCode.DIRECTOR,
            RoleCode.PROJECT_MANAGER,
        ]
