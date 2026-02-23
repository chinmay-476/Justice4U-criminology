import secrets
import threading
import time
from datetime import datetime

from flask import jsonify, render_template, request

from extensions import csrf
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


def _cleanup_rooms():
    now = _now_ts()
    stale_rooms = []
    for room_id, room in list(_VIDEO_ROOMS.items()):
        # Remove stale participants first.
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
        return render_template("video_call.html", room_id=room_id, case_no=meeting.case_no, active=True)

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
