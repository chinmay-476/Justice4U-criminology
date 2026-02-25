import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import uuid
from datetime import datetime

from flask import current_app, jsonify, render_template, request

from extensions import csrf, db
from models import MeetingLink

_ROOM_LOCK = threading.Lock()
_ROOM_TTL_SECONDS = 60 * 60 * 3
_ROOM_PARTICIPANT_TIMEOUT_SECONDS = 60 * 3
_MAX_ROOM_EVENTS = 400
_MAX_CHAT_TEXT_LENGTH = 1000
_MAX_CHAT_IMAGE_DATA_LENGTH = 2_000_000
_VIDEO_ROOMS = {}


def _now_ts():
    return int(time.time())


def _b64url_encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def _create_hs256_jwt(payload, secret):
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(str(secret).encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _b64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def _sanitize_display_name(value):
    text = str(value or "").strip()
    if not text:
        return "Participant"
    return text[:80]


def _normalize_turn_urls(raw_value):
    if isinstance(raw_value, str):
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    if isinstance(raw_value, (list, tuple)):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    return []


def _build_ice_servers():
    ice_servers = [{"urls": ["stun:stun.l.google.com:19302"]}]

    turn_urls = _normalize_turn_urls(current_app.config.get("VIDEO_TURN_URLS"))
    if turn_urls:
        turn_server = {"urls": turn_urls}
        username = (current_app.config.get("VIDEO_TURN_USERNAME") or "").strip()
        credential = (current_app.config.get("VIDEO_TURN_CREDENTIAL") or "").strip()
        if username and credential:
            turn_server["username"] = username
            turn_server["credential"] = credential
        ice_servers.append(turn_server)

    return ice_servers


def _internal_request_authorized():
    configured_token = str(current_app.config.get("VIDEO_SIGNALING_INTERNAL_TOKEN") or "").strip()
    header_token = str(request.headers.get("X-Internal-Token") or "").strip()
    return bool(configured_token and header_token and hmac.compare_digest(configured_token, header_token))


def _safe_ws_path():
    path = str(current_app.config.get("VIDEO_WS_PATH") or "/ws/socket.io").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    return path


def _cleanup_rooms():
    now = _now_ts()
    stale_rooms = []
    for room_id, room in list(_VIDEO_ROOMS.items()):
        stale_participants = [
            client_id
            for client_id, participant in room["participants"].items()
            if now - participant["last_seen"] > _ROOM_PARTICIPANT_TIMEOUT_SECONDS
        ]
        for client_id in stale_participants:
            room["participants"].pop(client_id, None)

        is_stale = (now - room["updated_at"] > _ROOM_TTL_SECONDS) or not room["participants"]
        if is_stale:
            stale_rooms.append(room_id)

    for room_id in stale_rooms:
        _VIDEO_ROOMS.pop(room_id, None)


def _get_room(room_id, create=False):
    room = _VIDEO_ROOMS.get(room_id)
    if room or not create:
        return room
    room = {
        "next_event_id": 1,
        "events": [],
        "participants": {},
        "updated_at": _now_ts(),
    }
    _VIDEO_ROOMS[room_id] = room
    return room


def _append_event(room, sender, event_type, payload=None):
    event = {
        "id": room["next_event_id"],
        "sender": sender,
        "type": event_type,
        "payload": payload or {},
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    room["next_event_id"] += 1
    room["events"].append(event)
    if len(room["events"]) > _MAX_ROOM_EVENTS:
        room["events"] = room["events"][-_MAX_ROOM_EVENTS:]
    room["updated_at"] = _now_ts()
    return event


def _active_meeting_by_room(room_id):
    return (
        MeetingLink.query.filter_by(status="Ongoing")
        .filter(MeetingLink.link.like(f"%/video-call/{room_id}%"))
        .order_by(MeetingLink.created_at.desc())
        .first()
    )


def register_video_call_routes(app):
    @app.route("/video-call/<room_id>")
    def video_call_room(room_id):
        meeting = _active_meeting_by_room(room_id)
        if not meeting:
            return render_template("video_call.html", room_id=room_id, case_no=None, active=False), 404
        return render_template(
            "video_call.html",
            room_id=room_id,
            case_no=meeting.case_no,
            active=True,
            signaling_mode=app.config.get("VIDEO_SIGNALING_MODE", "hybrid"),
            ws_path=_safe_ws_path(),
        )

    @app.route("/api/video-call/<room_id>/token", methods=["POST"])
    @csrf.exempt
    def video_call_token(room_id):
        meeting = _active_meeting_by_room(room_id)
        if not meeting:
            return jsonify({"success": False, "message": "Call room is inactive"}), 404

        request_data = request.get_json(silent=True) or {}
        display_name = _sanitize_display_name(request_data.get("display_name"))
        ttl = max(60, int(current_app.config.get("VIDEO_SIGNALING_TOKEN_TTL_SECONDS", 300)))
        now = _now_ts()

        with _ROOM_LOCK:
            _cleanup_rooms()
            room = _get_room(room_id, create=False)
            participants_hint = len(room["participants"]) if room else 1

        payload = {
            "sub": f"participant-{uuid.uuid4().hex[:12]}",
            "room_id": room_id,
            "case_no": meeting.case_no,
            "display_name": display_name,
            "iat": now,
            "exp": now + ttl,
            "jti": uuid.uuid4().hex,
        }
        token = _create_hs256_jwt(payload, current_app.config.get("VIDEO_SIGNALING_JWT_SECRET") or app.secret_key)

        return jsonify(
            {
                "success": True,
                "token": token,
                "room_id": room_id,
                "ws_path": _safe_ws_path(),
                "expires_in": ttl,
                "participants_hint": participants_hint,
                "signaling_mode": current_app.config.get("VIDEO_SIGNALING_MODE", "hybrid"),
            }
        )

    @app.route("/api/video-call/<room_id>/ice-config", methods=["GET"])
    @csrf.exempt
    def video_call_ice_config(room_id):
        if not _active_meeting_by_room(room_id):
            return jsonify({"success": False, "message": "Call room is inactive"}), 404

        return jsonify(
            {
                "success": True,
                "ice_servers": _build_ice_servers(),
                "signaling_mode": current_app.config.get("VIDEO_SIGNALING_MODE", "hybrid"),
            }
        )

    @app.route("/internal/video-call/<room_id>/status", methods=["GET"])
    @csrf.exempt
    def internal_video_call_status(room_id):
        if not _internal_request_authorized():
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        meeting = _active_meeting_by_room(room_id)
        if not meeting:
            return jsonify({"active": False, "case_no": None, "ended_at": None})

        ended_at = None
        if meeting.ended_at:
            ended_at = meeting.ended_at.isoformat() + "Z"

        return jsonify(
            {
                "active": True,
                "case_no": meeting.case_no,
                "ended_at": ended_at,
            }
        )

    @app.route("/internal/video-call/<room_id>/terminate", methods=["POST"])
    @csrf.exempt
    def internal_video_call_terminate(room_id):
        if not _internal_request_authorized():
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        meeting = _active_meeting_by_room(room_id)
        if meeting:
            meeting.status = "Ended"
            meeting.ended_at = datetime.utcnow()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                return jsonify({"success": False, "message": "Failed to terminate room"}), 500

        with _ROOM_LOCK:
            _VIDEO_ROOMS.pop(room_id, None)

        return jsonify({"success": True, "room_id": room_id, "active": False})

    @app.route("/api/video-call/<room_id>/join", methods=["POST"])
    @csrf.exempt
    def video_call_join(room_id):
        if not _active_meeting_by_room(room_id):
            return jsonify({"success": False, "message": "Call room is inactive"}), 404

        with _ROOM_LOCK:
            _cleanup_rooms()
            room = _get_room(room_id, create=True)
            client_id = secrets.token_urlsafe(12)
            room["participants"][client_id] = {"last_seen": _now_ts()}
            room["updated_at"] = _now_ts()
            participants = len(room["participants"])
            if participants > 1:
                _append_event(room, client_id, "participant_joined", {"participants": participants})
            return jsonify(
                {
                    "success": True,
                    "client_id": client_id,
                    "participants": participants,
                    "is_initiator": participants == 1,
                    "last_event_id": room["next_event_id"] - 1,
                }
            )

    @app.route("/api/video-call/<room_id>/events", methods=["GET"])
    @csrf.exempt
    def video_call_events(room_id):
        client_id = (request.args.get("client_id") or "").strip()
        last_event_id = request.args.get("last_event_id", 0, type=int)
        if not client_id:
            return jsonify({"success": False, "message": "Missing client_id"}), 400

        with _ROOM_LOCK:
            _cleanup_rooms()
            room = _get_room(room_id, create=False)
            if not room or client_id not in room["participants"]:
                return jsonify({"success": False, "message": "Session not found"}), 404

            room["participants"][client_id]["last_seen"] = _now_ts()
            room["updated_at"] = _now_ts()

            events = [
                event
                for event in room["events"]
                if event["id"] > last_event_id and event["sender"] != client_id
            ]
            return jsonify(
                {
                    "success": True,
                    "events": events,
                    "last_event_id": room["next_event_id"] - 1,
                    "participants": len(room["participants"]),
                }
            )

    @app.route("/api/video-call/<room_id>/signal", methods=["POST"])
    @csrf.exempt
    def video_call_signal(room_id):
        data = request.get_json(silent=True) or {}
        client_id = (data.get("client_id") or "").strip()
        signal_type = (data.get("type") or "").strip()
        payload = data.get("payload") or {}

        allowed_signal_types = {"offer", "answer", "candidate", "hangup", "chat_text", "chat_image"}
        if not client_id or signal_type not in allowed_signal_types:
            return jsonify({"success": False, "message": "Invalid payload"}), 400

        if signal_type == "chat_text":
            message = str(payload.get("message", "")).strip()
            if not message:
                return jsonify({"success": False, "message": "Message is empty"}), 400
            if len(message) > _MAX_CHAT_TEXT_LENGTH:
                return jsonify({"success": False, "message": "Message is too long"}), 400
            payload = {"message": message}

        if signal_type == "chat_image":
            image_data = str(payload.get("image_data", "")).strip()
            if not image_data.startswith("data:image/"):
                return jsonify({"success": False, "message": "Invalid image payload"}), 400
            if len(image_data) > _MAX_CHAT_IMAGE_DATA_LENGTH:
                return jsonify({"success": False, "message": "Image is too large"}), 400
            payload = {"image_data": image_data}

        with _ROOM_LOCK:
            room = _get_room(room_id, create=False)
            if not room or client_id not in room["participants"]:
                return jsonify({"success": False, "message": "Session not found"}), 404

            room["participants"][client_id]["last_seen"] = _now_ts()
            _append_event(room, client_id, signal_type, payload)
            return jsonify({"success": True})

    @app.route("/api/video-call/<room_id>/leave", methods=["POST"])
    @csrf.exempt
    def video_call_leave(room_id):
        data = request.get_json(silent=True) or {}
        client_id = (data.get("client_id") or "").strip()
        if not client_id:
            return jsonify({"success": False, "message": "Missing client_id"}), 400

        with _ROOM_LOCK:
            room = _get_room(room_id, create=False)
            if not room:
                return jsonify({"success": True})

            room["participants"].pop(client_id, None)
            _append_event(room, client_id, "participant_left", {})
            if not room["participants"]:
                _VIDEO_ROOMS.pop(room_id, None)
            return jsonify({"success": True})
