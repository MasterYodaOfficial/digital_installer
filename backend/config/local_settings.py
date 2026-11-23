"""Настройки локальной разработки с отдельной БД и медиа."""
from .settings import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
TIME_ZONE = "Asia/Yekaterinburg"
WORKDAY_BYPASS_GPS = False
# Даже случайно заданные production POSTGRES_* не направят локальный запуск на VPS.
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "digital_installer_local",
    "USER": "digital_local",
    "PASSWORD": os.environ["LOCAL_POSTGRES_PASSWORD"],
    "HOST": "127.0.0.1",
    "PORT": "55432",
}}
MEDIA_ROOT = BASE_DIR / "local-media"
