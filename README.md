# Цифровой монтажник

Веб-приложение для учёта смен, посещений объектов и работы бригад. Проект развивается; наличие страницы не означает завершённую приёмку функции.

## Структура

- `backend/` — Django, DRF, JWT, PostgreSQL.
- `backend/apps/users/` — сотрудники, роли и бригады.
- `backend/apps/objects/` — объекты, стадии, документы и планы.
- `backend/apps/pricing/` — расценки и группы работ.
- `backend/apps/workday/` — смены, посещения, работы и отчёты.
- `frontend/` — React, Vite, Material UI, инфраструктура PWA.
- `docs/` — техническая документация.

План функций: [TODO.md](TODO.md). Изменения: [CHANGELOG.md](CHANGELOG.md). Правила доработок: [CONTRIBUTING.md](CONTRIBUTING.md).

## Локальный запуск

Рекомендуемый изолированный вариант: [локальная PostgreSQL и демонстрационные учётные записи](docs/local-development.md).

1. Создайте виртуальное окружение Python и установите `backend/requirements.txt`.
2. Скопируйте `.env.example` в `.env`, задайте локальные параметры PostgreSQL и секретный ключ. Не публикуйте `.env`.
3. Из `backend` выполните `python manage.py migrate`, `python manage.py createsuperuser`, `python manage.py runserver`.
4. Из `frontend` выполните `npm ci` и `npm run dev`.

Python виртуального окружения из корня: `.venv/Scripts/python.exe` в Windows, `.venv/bin/python` в Linux.

## Проверка

Из `backend` с Python виртуального окружения:

```text
python manage.py test apps.users --settings=config.test_settings
```

Тесты используют SQLite в памяти и не требуют рабочих данных. Эти настройки нельзя использовать на рабочем сервере. Для изменений моделей нужна также проверка PostgreSQL.

## Ограничения

Полноценный офлайн пока не готов. Права необходимо проверять на сервере, а не только скрывать кнопки. `scripts/setup-server.sh` — первоначальная установка с изменением настроек БД и служб, не команда обновления.

Смена Git remote не обновляет опубликованную сборку. Выкладка выполняется отдельно с резервированием и проверкой.

## Документация функций

- [Управление пользователями](docs/user-management.md).
