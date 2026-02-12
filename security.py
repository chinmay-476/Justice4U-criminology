import os
import re
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import request
from werkzeug.utils import secure_filename

_LOGIN_ATTEMPTS = {}

LOGIN_WINDOW_SECONDS = 10 * 60
LOGIN_BLOCK_SECONDS = 15 * 60
MAX_LOGIN_ATTEMPTS = 5


def _now_utc():
    return datetime.utcnow()


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def check_login_block(scope):
    now = _now_utc()
    key = f'{scope}:{_client_ip()}'
    data = _LOGIN_ATTEMPTS.get(key)
    if not data:
        return False, 0
    blocked_until = data.get('blocked_until')
    if blocked_until and blocked_until > now:
        return True, int((blocked_until - now).total_seconds())
    if data.get('first_attempt') and (now - data['first_attempt']).total_seconds() > LOGIN_WINDOW_SECONDS:
        _LOGIN_ATTEMPTS.pop(key, None)
    return False, 0


def record_login_failure(scope):
    now = _now_utc()
    key = f'{scope}:{_client_ip()}'
    data = _LOGIN_ATTEMPTS.get(key)
    if not data or (now - data['first_attempt']).total_seconds() > LOGIN_WINDOW_SECONDS:
        data = {'count': 0, 'first_attempt': now, 'blocked_until': None}
    data['count'] += 1
    if data['count'] >= MAX_LOGIN_ATTEMPTS:
        data['blocked_until'] = now + timedelta(seconds=LOGIN_BLOCK_SECONDS)
    _LOGIN_ATTEMPTS[key] = data


def clear_login_failures(scope):
    key = f'{scope}:{_client_ip()}'
    _LOGIN_ATTEMPTS.pop(key, None)


def save_validated_upload(file_obj, upload_folder, prefix, allowed_extensions, max_size_bytes):
    if not file_obj or not file_obj.filename:
        return None

    original_name = secure_filename(file_obj.filename)
    if '.' not in original_name:
        raise ValueError('Invalid file name.')

    extension = original_name.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        raise ValueError('Unsupported file type.')

    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)

    if size > max_size_bytes:
        raise ValueError('Uploaded file is too large.')

    unique_name = f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{extension}"
    file_obj.save(os.path.join(upload_folder, unique_name))
    return unique_name


def is_valid_meeting_link(link):
    if not link or len(link) > 500:
        return False
    parsed = urlparse(link)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)


def is_valid_case_no(case_no):
    if not case_no:
        return False
    return bool(re.fullmatch(r'[A-Za-z0-9_/\\-]{1,50}', case_no.strip()))
