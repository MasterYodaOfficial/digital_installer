# Локальная разработка

Локальная БД отделена от VPS. Никакие команды ниже не обращаются к рабочему серверу.

## Подготовка

Нужны Python, Node.js с npm и запущенный Docker Desktop. Установите зависимости Python в `.venv`, затем выполните `npm ci` в `frontend`.

В корневом `.env` задайте случайные значения `LOCAL_POSTGRES_PASSWORD` и `DJANGO_SECRET_KEY`. Файл исключён из Git. Не копируйте настройки и данные рабочей БД.

Из корня:

```text
docker compose -p digital-installer-local -f compose.local.yaml up -d --wait
```

PostgreSQL 16 доступна только на `127.0.0.1:55432`; база `digital_installer_local`, пользователь `digital_local`. Данные сохраняются в отдельном Docker-томе. `config.local_settings` жёстко задаёт локальный адрес и имя БД.

Из `backend` с Python окружения:

```text
python manage.py migrate --settings=config.local_settings
python manage.py seed_local_demo --settings=config.local_settings
python manage.py runserver 127.0.0.1:8000 --settings=config.local_settings
```

Команда демоданных создаёт директора, РП, мастера, монтажника и технического администратора. Существующие записи не перезаписывает; случайные пароли находятся в `.local/demo-accounts.json`, исключённом из Git. Команда отказывается запускаться с другими настройками или БД.

Из `frontend`: `npm run dev`. Адрес приложения — `http://127.0.0.1:5173`. Vite перенаправляет `/api` и `/media` только на локальный Django. Не задавайте `VITE_API_URL` с адресом VPS.

## Проверки

- Быстрые проверки на SQLite: `python manage.py test apps.users --settings=config.test_settings`.
- На отдельной тестовой PostgreSQL: `python manage.py test apps.users --settings=config.local_settings`. Django создаёт и удаляет тестовую БД, не демоданные.
- Сборка интерфейса из `frontend`: `npm run build`.
- Войти как `demo_director`, открыть «Сотрудники», создать РП; войти как `demo_pm` и убедиться, что доступны только мастер и монтажник.
- После редактирования проверить сохранение и вход под новым пользователем. Сетевые ошибки не должны закрывать форму как успешно сохранённую.

## Остановка

Остановите процессы Django/Vite через Ctrl+C в их терминалах. `docker compose -p digital-installer-local -f compose.local.yaml stop` останавливает БД без удаления данных. Не используйте `down -v`, если нужно сохранить демоданные.

Если серверы запущены помощником в фоне, их идентификаторы находятся в `.local/processes.json`, журналы — в `.local/backend*.log` и `.local/frontend*.log`. Перед остановкой проверьте имя процесса по PID; сохранённые PID после перезагрузки могут относиться к другим процессам.
