# Realtime Signaling Service

Node.js Socket.IO service for Justice4U criminology video calls.

## Run

```bash
cd realtime_signaling
npm install
npm run start
```

Default port: `5050`
Default socket path: `/ws/socket.io`

## Required Environment Variables

- `SIGNALING_JWT_SECRET` (must match Flask `VIDEO_SIGNALING_JWT_SECRET`, default `dev-signaling-secret`)
- `INTERNAL_API_TOKEN` (must match Flask `VIDEO_SIGNALING_INTERNAL_TOKEN`, default `dev-internal-token`)
- `FLASK_INTERNAL_BASE_URL` (default `http://127.0.0.1:5000`)
- `REDIS_URL` (default `redis://127.0.0.1:6379`)

Optional:

- `PORT` (default `5050`)
- `WS_PATH` (default `/ws/socket.io`)
- `ALLOWED_ORIGIN` (same-domain recommended)
- `ROOM_TTL_SECONDS` (default 10800)
- `PARTICIPANT_TTL_SECONDS` (default 300)
