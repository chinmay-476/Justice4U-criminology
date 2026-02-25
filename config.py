import os
from datetime import timedelta


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_list(name, default=None):
    value = os.getenv(name)
    if value is None:
        return list(default or [])
    items = [item.strip() for item in value.split(',') if item.strip()]
    return items or list(default or [])


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:chin1987@localhost:3306/criminology'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv('SESSION_LIFETIME_HOURS', '8')))
    APP_ENV = os.getenv('FLASK_ENV', os.getenv('ENV', 'development')).strip().lower()
    ENABLE_DEV_DOCS = _env_bool('ENABLE_DEV_DOCS', default=(APP_ENV != 'production'))
    VIDEO_SIGNALING_MODE = os.getenv('VIDEO_SIGNALING_MODE', 'hybrid').strip().lower()
    if VIDEO_SIGNALING_MODE not in {'hybrid', 'ws_only', 'polling_only'}:
        VIDEO_SIGNALING_MODE = 'hybrid'
    VIDEO_SIGNALING_JWT_SECRET = os.getenv('VIDEO_SIGNALING_JWT_SECRET', 'dev-signaling-secret')
    VIDEO_SIGNALING_TOKEN_TTL_SECONDS = _env_int('VIDEO_SIGNALING_TOKEN_TTL_SECONDS', 300)
    VIDEO_SIGNALING_INTERNAL_TOKEN = os.getenv('VIDEO_SIGNALING_INTERNAL_TOKEN', 'dev-internal-token')
    VIDEO_SIGNALING_INTERNAL_URL = os.getenv('VIDEO_SIGNALING_INTERNAL_URL', 'http://127.0.0.1:5050')
    VIDEO_WS_PATH = os.getenv('VIDEO_WS_PATH', '/ws/socket.io').strip() or '/ws/socket.io'
    VIDEO_TURN_URLS = _env_list('VIDEO_TURN_URLS')
    VIDEO_TURN_USERNAME = os.getenv('VIDEO_TURN_USERNAME', '').strip()
    VIDEO_TURN_CREDENTIAL = os.getenv('VIDEO_TURN_CREDENTIAL', '').strip()
    VIDEO_ALLOWED_ORIGIN = os.getenv('VIDEO_ALLOWED_ORIGIN', '').strip()
