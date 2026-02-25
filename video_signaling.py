import json
import urllib.error
import urllib.parse
import urllib.request


def extract_room_id_from_link(link):
    if not link:
        return None

    raw = str(link).strip()
    if not raw:
        return None

    parsed = urllib.parse.urlparse(raw)
    path = parsed.path if parsed.scheme or parsed.netloc else raw
    marker = '/video-call/'
    if marker not in path:
        return None

    room_part = path.split(marker, 1)[1].strip().strip('/')
    if not room_part:
        return None
    return room_part.split('/', 1)[0]


def notify_signaling_terminate(config, room_id, reason='meeting_ended'):
    if not room_id:
        return False

    base_url = (config.get('VIDEO_SIGNALING_INTERNAL_URL') or '').strip().rstrip('/')
    internal_token = (config.get('VIDEO_SIGNALING_INTERNAL_TOKEN') or '').strip()
    if not base_url or not internal_token:
        return False

    endpoint = f"{base_url}/internal/video-call/{urllib.parse.quote(str(room_id), safe='')}/terminate"
    payload = json.dumps({'reason': reason}).encode('utf-8')
    request_obj = urllib.request.Request(
        endpoint,
        method='POST',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'X-Internal-Token': internal_token,
        },
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=2) as response:
            return 200 <= int(getattr(response, 'status', 500)) < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False
