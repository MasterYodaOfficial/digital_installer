from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from django.utils import timezone
from apps.workday.models import WorkDay, WorkDayStatus
from apps.workday.serializers import ClockInSerializer
from rest_framework import serializers

from .models import Brigade, RoleCode, User, UserStatus
from .views import CurrentUserView, UserAdminViewSet


class UserManagementTests(TestCase):
    def test_profile_exposes_only_assignable_roles(self):
        request = self.factory.get('/api/auth/me/')
        force_authenticate(request, user=self.pm)
        response = CurrentUserView.as_view()(request)
        self.assertEqual({r['value'] for r in response.data['manageable_roles']}, {RoleCode.FOREMAN, RoleCode.WORKER})

    def test_list_marks_protected_accounts_read_only(self):
        request = self.factory.get('/api/admin/users/')
        force_authenticate(request, user=self.pm)
        response = UserAdminViewSet.as_view({'get': 'list'})(request)
        editable = {row['id']: row['can_edit'] for row in response.data}
        self.assertTrue(editable[self.worker.pk])
        self.assertFalse(editable[self.pm.pk])
        self.assertFalse(editable[self.technical.pk])

    def test_new_password_allows_login_and_is_not_returned(self):
        response = self.call(self.pm, 'post', {'username': 'new_login', 'password': 'LocalTest-4821'})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        user = User.objects.get(username='new_login')
        self.assertTrue(user.check_password('LocalTest-4821'))

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

    def make_shift(self, status):
        """Создаёт изолированную смену с историческим участием монтажника."""
        brigade = Brigade.objects.create(name='Тестовая', foreman=self.pm)
        shift = WorkDay.objects.create(brigade=brigade, foreman=self.pm,
                                       date=timezone.localdate(), clock_in_at=timezone.now(), status=status)
        shift.workers_present.add(self.worker)
        return shift

    def test_archive_and_restore_preserve_history_and_password(self):
        shift = self.make_shift(WorkDayStatus.CLOSED)
        self.worker.set_password('Archive-Test-4821')
        self.worker.save()
        for target_status, active in ((UserStatus.DISMISSED, False), (UserStatus.ACTIVE, True)):
            response = self.call(self.pm, 'patch', {'status': target_status}, self.worker)
            self.assertEqual(response.status_code, 200)
            self.worker.refresh_from_db()
            self.assertEqual(self.worker.is_active, active)
            self.assertEqual(self.worker.status, target_status)
            self.assertTrue(self.worker.check_password('Archive-Test-4821'))
            self.assertTrue(shift.workers_present.filter(pk=self.worker.pk).exists())

    def test_archive_requires_closed_shift_for_worker_and_foreman(self):
        self.make_shift(WorkDayStatus.OPEN)
        for target in (self.worker, self.pm):
            response = self.call(self.director, 'patch', {'status': UserStatus.DISMISSED}, target)
            self.assertEqual(response.status_code, 400)
            target.refresh_from_db()
            self.assertTrue(target.is_active)

    def test_archive_cannot_bypass_protected_account_permissions(self):
        for target in (self.pm, self.director, self.technical):
            self.assertEqual(self.call(self.pm, 'patch', {'status': UserStatus.DISMISSED}, target).status_code, 403)

    def test_physical_delete_disabled_even_for_technical_admin(self):
        for actor in (self.pm, self.technical):
            self.assertEqual(self.call(actor, 'delete', target=self.worker).status_code, 405)
            self.assertTrue(User.objects.filter(pk=self.worker.pk).exists())

    def test_archive_list_filters(self):
        self.call(self.pm, 'patch', {'status': UserStatus.DISMISSED}, self.worker)
        for archived, expected in (('true', True), ('false', False)):
            request = self.factory.get('/', {'archived': archived})
            force_authenticate(request, user=self.pm)
            response = UserAdminViewSet.as_view({'get': 'list'})(request)
            self.assertEqual(self.worker.pk in {row['id'] for row in response.data}, expected)

    def test_archive_blocks_login_and_existing_access_token_until_restore(self):
        client = APIClient()
        credentials = {'username': self.worker.username, 'password': 'Archive-Test-4821'}
        self.worker.set_password(credentials['password'])
        self.worker.save()
        login = client.post('/api/auth/token/', credentials)
        self.assertEqual(login.status_code, 200)
        token = login.data['access']
        self.call(self.pm, 'patch', {'status': UserStatus.DISMISSED}, self.worker)
        self.assertEqual(client.post('/api/auth/token/', credentials).status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)
        self.call(self.pm, 'patch', {'status': UserStatus.ACTIVE}, self.worker)
        client.credentials()
        self.assertEqual(client.post('/api/auth/token/', credentials).status_code, 200)

    def test_legacy_blocked_status_denies_login_and_existing_token(self):
        client = APIClient()
        self.worker.set_password('Archive-Test-4821')
        self.worker.save()
        credentials = {'username': self.worker.username, 'password': 'Archive-Test-4821'}
        token = client.post('/api/auth/token/', credentials).data['access']
        User.objects.filter(pk=self.worker.pk).update(status=UserStatus.BLOCKED)
        self.assertEqual(client.post('/api/auth/token/', credentials).status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)

    def test_editing_archived_employee_does_not_restore_access(self):
        self.call(self.pm, 'patch', {'status': UserStatus.DISMISSED}, self.worker)
        self.call(self.pm, 'patch', {'first_name': 'Иван', 'is_active': True}, self.worker)
        self.worker.refresh_from_db()
        self.assertFalse(self.worker.is_active)

    def test_new_shift_rejects_unavailable_workers(self):
        validator = ClockInSerializer()
        self.assertEqual(validator.validate_workers_present([self.worker.pk]), [self.worker.pk])
        for target_status in (UserStatus.DISMISSED, UserStatus.BLOCKED):
            User.objects.filter(pk=self.worker.pk).update(status=target_status)
            with self.assertRaises(serializers.ValidationError):
                validator.validate_workers_present([self.worker.pk])
        with self.assertRaises(serializers.ValidationError):
            validator.validate_workers_present([999999])
