"""Создание демонстрационных пользователей только в локальной базе."""
import json
import secrets
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.users.models import RoleCode, User


class Command(BaseCommand):
    help = 'Создать локальные тестовые учётные записи, не изменяя существующие'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        if (settings.SETTINGS_MODULE != 'config.local_settings' or
                db['HOST'] != '127.0.0.1' or db['NAME'] != 'digital_installer_local'):
            raise CommandError('Команда разрешена только с config.local_settings и локальной БД')
        output = settings.BASE_DIR.parent / '.local' / 'demo-accounts.json'
        output.parent.mkdir(exist_ok=True)
        accounts = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
        with transaction.atomic():
            for username, role in [('demo_director', RoleCode.DIRECTOR), ('demo_pm', RoleCode.PROJECT_MANAGER), ('demo_foreman', RoleCode.FOREMAN), ('demo_worker', RoleCode.WORKER), ('demo_admin', RoleCode.ADMINISTRATOR)]:
                if User.objects.filter(username=username).exists():
                    continue
                password = secrets.token_urlsafe(15)
                User.objects.create_user(username=username, password=password, role=role,
                                         first_name='Демо', last_name=role.label,
                                         is_staff=role == RoleCode.ADMINISTRATOR,
                                         is_superuser=role == RoleCode.ADMINISTRATOR)
                accounts[username] = password
            output.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(f'Локальные учётные записи готовы. Доступы: {output}')
