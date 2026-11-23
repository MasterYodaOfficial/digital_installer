from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .models import RoleCode, User
from .views import UserAdminViewSet


class UserManagementTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.pm = User.objects.create_user(username="pm", role=RoleCode.PROJECT_MANAGER)
        self.director = User.objects.create_user(username="director", role=RoleCode.DIRECTOR)
        self.worker = User.objects.create_user(username="worker", role=RoleCode.WORKER)
        self.technical = User.objects.create_superuser(username="technical", password="test", role=RoleCode.ADMINISTRATOR)

    def call(self, actor, method, data=None, target=None):
        request = getattr(self.factory, method)("/", data or {}, format="json")
        force_authenticate(request, user=actor)
        action = {"post": "create", "patch": "partial_update", "delete": "destroy"}[method]
        return UserAdminViewSet.as_view({method: action})(request, **({"pk": target.pk} if target else {}))

    def test_pm_creates_worker_and_foreman(self):
        for role in (RoleCode.WORKER, RoleCode.FOREMAN):
            response = self.call(self.pm, "post", {"username": "new_" + role, "role": role})
            self.assertEqual(response.status_code, 201)

    def test_pm_cannot_create_privileged_roles(self):
        for role in (RoleCode.PROJECT_MANAGER, RoleCode.DIRECTOR, RoleCode.ADMINISTRATOR):
            response = self.call(self.pm, "post", {"username": "new_" + role, "role": role})
            self.assertEqual(response.status_code, 400)
            self.assertFalse(User.objects.filter(username="new_" + role).exists())

    def test_director_creates_pm_but_not_director(self):
        self.assertEqual(self.call(self.director, "post", {"username": "new_pm", "role": RoleCode.PROJECT_MANAGER}).status_code, 201)
        self.assertEqual(self.call(self.director, "post", {"username": "new_director", "role": RoleCode.DIRECTOR}).status_code, 400)

    def test_pm_cannot_promote_worker(self):
        self.assertEqual(self.call(self.pm, "patch", {"role": RoleCode.DIRECTOR}, self.worker).status_code, 400)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.role, RoleCode.WORKER)

    def test_pm_cannot_edit_self_or_director_or_technical(self):
        for target in (self.pm, self.director, self.technical):
            self.assertEqual(self.call(self.pm, "patch", {"password": "replacement"}, target).status_code, 403)
            self.assertEqual(self.call(self.pm, "delete", target=target).status_code, 403)

    def test_staff_account_is_protected_even_with_worker_role(self):
        self.worker.is_staff = True
        self.worker.save()
        self.assertEqual(self.call(self.director, "patch", {"password": "replacement"}, self.worker).status_code, 403)

    def test_legacy_director_superuser_cannot_bypass_business_limits(self):
        self.director.is_superuser = True
        self.director.save()
        self.assertEqual(self.call(self.director, "post", {"username": "another_admin", "role": RoleCode.ADMINISTRATOR}).status_code, 400)

    def test_worker_cannot_manage_users(self):
        self.assertEqual(self.call(self.worker, "post", {"username": "new"}).status_code, 403)

    def test_technical_admin_can_manage_roles(self):
        self.assertEqual(self.call(self.technical, "patch", {"role": RoleCode.PROJECT_MANAGER}, self.worker).status_code, 200)

    def test_pm_can_edit_worker_and_omitted_role_defaults_to_worker(self):
        self.assertEqual(self.call(self.pm, "patch", {"first_name": "Updated"}, self.worker).status_code, 200)
        response = self.call(self.pm, "post", {"username": "default_role"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["role"], RoleCode.WORKER)
