# Criminology Management System

Flask application for criminal case records, complaint tracking, section/punishment lookup, and role-based workflows (Admin, Super Admin, Judge).

## Stack

- Flask + SQLAlchemy + Flask-WTF
- Database via `DATABASE_URL` (MySQL default, SQLite optional)
- Jinja templates + AdminLTE UI
- WebRTC media + Socket.IO signaling (Node.js) with polling fallback

## Project Layout

- `app.py`: app creation, extension init, startup checks, route registration
- `config.py`: configuration from environment (`ENABLE_DEV_DOCS` included)
- `db_init.py`: schema checks + master auth seed/upsert
- `models.py`: SQLAlchemy models (`MasterAuth` added)
- `decorators.py`: role guards
- `security.py`: validation + login throttling helpers
- `video_signaling.py`: internal room-id parsing + signaling termination webhooks
- `routes/`:
  - `public_routes.py`
  - `admin_routes.py`
  - `super_admin_routes.py`
  - `judge_routes.py`
  - `video_call_routes.py`
  - `dev_docs_routes.py`
- `realtime_signaling/`: Node.js Socket.IO service + Redis room store
- `templates/admin_dev_guide.html`: protected web onboarding guide
- `tests/test_security_utils.py`
- `tests/test_auth_dev_docs_video_call.py`

## Authentication

### Existing paths (preserved)

- `/admin-login`: admin table with hashed password
- `/super_admin_login`: env-based super-admin fallback
- `/judge-login`: env-based judge login

### Master authentication (additive)

New table/model: `master_auth`

- `email` (unique)
- `password_hash`
- `can_admin`
- `can_super_admin`
- `is_active`
- timestamps

Seeded at startup (idempotent upsert):

- Email: `chinmaysahoo63715@gmail.com`
- Password source: `chin1987` (stored only as hash)
- Role flags: admin + super_admin enabled

Role scope in this project:

- Master auth applies to **admin** and **super admin**
- No additional user-login master path added (no user login flow exists)

## Developer Onboarding Portal

Route:

- `GET /admin/dev-guide`

Behavior:

- Requires `admin_or_super_admin_required`
- Returns `404` when docs are disabled
- Includes:
  - system and module map
  - frontend/template/static map
  - database schema snapshot from SQLAlchemy metadata
  - API inventory from `app.url_map`
  - realtime/video-call architecture
  - run/test commands
  - prioritized automation backlog (P0-P3)
  - current video-call validation status panel

## Video Call Notes

Implemented flow:

- UI page: `/video-call/<room_id>`
- Flask signaling/presence fallback APIs:
  - `POST /api/video-call/<room_id>/join`
  - `GET /api/video-call/<room_id>/events`
  - `POST /api/video-call/<room_id>/signal`
  - `POST /api/video-call/<room_id>/leave`
- Flask realtime bootstrap APIs:
  - `POST /api/video-call/<room_id>/token`
  - `GET /api/video-call/<room_id>/ice-config`
- Flask internal APIs (Node integration):
  - `GET /internal/video-call/<room_id>/status`
  - `POST /internal/video-call/<room_id>/terminate`
- Node Socket.IO endpoint:
  - `/ws/socket.io` (same-domain reverse proxy recommended)
- Signal types:
  - `offer`, `answer`, `candidate`, `hangup`
  - `chat_text`, `chat_image`
- Startup auto-normalizes legacy third-party meeting URLs in ongoing records to in-app `/video-call/<room_id>` links.
- Judge/super-admin meeting-end flows notify the Node signaling service to terminate active websocket rooms.

UI refinement delivered:

- Judge pages now expose explicit **Join Video Call** button
- Judge accused table now has per-case **Join/Start Call** controls, so judge can join/create room directly for each accused row
- Secondary **Copy Link** affordance retained
- Judge video-call JSON endpoints now return explicit `401` JSON when judge session expires (instead of HTML redirect), improving in-page error handling.
- Admin/Super-Admin accused details modal now shows meeting actions (Join/Copy) when an active room exists for that case.

Known limitation:

- TURN is configurable but must be provisioned (`coturn`) for strict NAT/firewall networks.
- Single-device testing can be done with two browser windows/profiles (normal + incognito) joining the same room.

## Environment Variables

### Core

- `SECRET_KEY`
- `DATABASE_URL`
- `UPLOAD_FOLDER` (default `uploads`)
- `SESSION_COOKIE_SECURE` (enable in HTTPS production)
- `SESSION_COOKIE_SAMESITE` (default `Lax`)
- `SESSION_LIFETIME_HOURS` (default `8`)
- `VIDEO_SIGNALING_MODE` (`hybrid|ws_only|polling_only`, default `hybrid`)
- `VIDEO_SIGNALING_JWT_SECRET` (JWT signing key for signaling tokens, default `dev-signaling-secret`)
- `VIDEO_SIGNALING_TOKEN_TTL_SECONDS` (default `300`)
- `VIDEO_SIGNALING_INTERNAL_TOKEN` (shared internal token between Flask and Node, default `dev-internal-token`)
- `VIDEO_SIGNALING_INTERNAL_URL` (default `http://127.0.0.1:5050`)
- `VIDEO_WS_PATH` (default `/ws/socket.io`)
- `VIDEO_TURN_URLS` (comma-separated TURN URLs)
- `VIDEO_TURN_USERNAME`
- `VIDEO_TURN_CREDENTIAL`
- `VIDEO_ALLOWED_ORIGIN` (optional allowed origin for signaling service)

### Dev Docs

- `ENABLE_DEV_DOCS` (`true/false`)
- Default: enabled in non-production, disabled in production

### Master Auth

- `MASTER_AUTH_EMAIL` (default `chinmaysahoo63715@gmail.com`)
- `MASTER_AUTH_PASSWORD` (default `chin1987`)

### Existing Role Credentials (fallbacks retained)

- `SUPER_ADMIN_USERNAME`
- `SUPER_ADMIN_EMAIL`
- `SUPER_ADMIN_PASSWORD`
- `JUDGE_USERNAME`
- `JUDGE_PASSWORD`

## Run

### Flask app

From `flask_project/criminology/`:

```bash
pip install -r requirements.txt
python app.py
```

Default URL: `http://127.0.0.1:5000`

### Node signaling service

From `flask_project/criminology/realtime_signaling/`:

```bash
npm install
npm run start
```

Default URL: `http://127.0.0.1:5050` (behind Nginx in production)

### Infra for production reliability

- Redis (room state + rate counters)
- coturn (TURN relay for cross-network media)
- Nginx reverse proxy:
  - `/` -> Flask
  - `/ws/socket.io` -> Node signaling (websocket upgrade)
- Example Nginx config: `realtime_signaling/nginx.realtime.conf.example`

## Tests

From `flask_project/criminology/`:

```bash
python -m unittest tests/test_security_utils.py
python -m unittest tests/test_auth_dev_docs_video_call.py
```

From `flask_project/criminology/realtime_signaling/`:

```bash
npm test
```

## Manual QA Checklist (Video Call)

1. Two browsers in same network: join, text, image, hangup, rejoin.
2. Permission deny/allow cases for camera and microphone.
3. Cross-network run (Wi-Fi vs hotspot) with TURN to validate NAT behavior.
4. Stop Node service and verify hybrid fallback uses polling path.

## Judicial Automation Backlog (Prioritized)

- **P0** Security and reliability hardening (auth boundaries, CSRF surface, production call hardening)
- **P1** Paperwork elimination core (e-filing wizard, digital forms, role queue workflow)
- **P2** Automation layer (OCR extraction, auto-drafting, reminder/SLA timeline)
- **P3** Compliance/interoperability (tamper-evident logs, digital signatures, adapters)
