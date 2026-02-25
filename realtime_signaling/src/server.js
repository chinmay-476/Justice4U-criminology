const crypto = require('crypto');
const http = require('http');

const express = require('express');
const helmet = require('helmet');
const Redis = require('ioredis');
const { Server } = require('socket.io');

const { getClientIp, verifySocketToken } = require('./auth');
const { fetchRoomStatus } = require('./internalApi');
const { RoomStore } = require('./roomStore');
const { validateSignalPayload } = require('./validators');

const PORT = Number(process.env.PORT || 5050);
const REDIS_URL = process.env.REDIS_URL || 'redis://127.0.0.1:6379';
const SIGNALING_JWT_SECRET = process.env.SIGNALING_JWT_SECRET || 'dev-signaling-secret';
const INTERNAL_API_TOKEN = process.env.INTERNAL_API_TOKEN || 'dev-internal-token';
const FLASK_INTERNAL_BASE_URL = process.env.FLASK_INTERNAL_BASE_URL || 'http://127.0.0.1:5000';
const ALLOWED_ORIGIN = (process.env.ALLOWED_ORIGIN || '').trim();
const WS_PATH = normalizeWsPath(process.env.WS_PATH || '/ws/socket.io');
const ROOM_TTL_SECONDS = Number(process.env.ROOM_TTL_SECONDS || 60 * 60 * 3);
const PARTICIPANT_TTL_SECONDS = Number(process.env.PARTICIPANT_TTL_SECONDS || 60 * 5);

const JOIN_RATE_WINDOW_SECONDS = 30;
const JOIN_RATE_LIMIT = 40;
const SIGNAL_RATE_WINDOW_SECONDS = 10;
const SIGNAL_RATE_LIMIT = 150;

function normalizeWsPath(path) {
  const trimmed = String(path || '').trim();
  if (!trimmed) return '/ws/socket.io';
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

function makeLog(message, extra = {}) {
  const payload = {
    ts: new Date().toISOString(),
    message,
    ...extra,
  };
  console.log(JSON.stringify(payload));
}

const app = express();
app.use(helmet());
app.use(express.json({ limit: '2mb' }));

const redis = new Redis(REDIS_URL, {
  maxRetriesPerRequest: 2,
  enableReadyCheck: false,
});
redis.on('error', (error) => {
  makeLog('redis_error', { error: error.message });
});

const roomStore = new RoomStore(redis, {
  roomTtlSeconds: ROOM_TTL_SECONDS,
  participantTtlSeconds: PARTICIPANT_TTL_SECONDS,
});

function internalAuth(req, res, next) {
  const headerToken = String(req.headers['x-internal-token'] || '').trim();
  if (!INTERNAL_API_TOKEN || !headerToken || headerToken !== INTERNAL_API_TOKEN) {
    return res.status(401).json({ success: false, message: 'Unauthorized' });
  }
  return next();
}

app.get('/health', async (req, res) => {
  try {
    await redis.ping();
    return res.json({ status: 'ok', service: 'realtime-signaling', ws_path: WS_PATH });
  } catch (error) {
    return res.status(500).json({ status: 'error', message: error.message });
  }
});

const server = http.createServer(app);
const io = new Server(server, {
  path: WS_PATH,
  cors: {
    origin: ALLOWED_ORIGIN || true,
    credentials: true,
  },
  maxHttpBufferSize: 2_500_000,
  pingTimeout: 20000,
  pingInterval: 25000,
});

app.post('/internal/video-call/:roomId/terminate', internalAuth, async (req, res) => {
  const roomId = String(req.params.roomId || '').trim();
  if (!roomId) {
    return res.status(400).json({ success: false, message: 'Missing room id' });
  }

  const reason = String((req.body && req.body.reason) || 'terminated').trim() || 'terminated';
  const sockets = await io.in(roomId).fetchSockets();
  io.to(roomId).emit('room:terminated', { reason });
  sockets.forEach((socket) => socket.disconnect(true));
  await roomStore.clearRoom(roomId);
  makeLog('room_terminated', { roomId, reason, disconnected: sockets.length });
  return res.json({ success: true, room_id: roomId, disconnected: sockets.length });
});

io.use(async (socket, next) => {
  try {
    const origin = String((socket.handshake && socket.handshake.headers && socket.handshake.headers.origin) || '').trim();
    if (ALLOWED_ORIGIN && origin && origin !== ALLOWED_ORIGIN) {
      throw new Error('Origin not allowed');
    }

    const ipAddress = getClientIp(socket);
    const joinAllowed = await roomStore.checkRate(ipAddress, 'join', JOIN_RATE_WINDOW_SECONDS, JOIN_RATE_LIMIT);
    if (!joinAllowed) {
      throw new Error('Join rate limit exceeded');
    }

    const token = socket.handshake && socket.handshake.auth ? socket.handshake.auth.token : null;
    const payload = verifySocketToken(token, SIGNALING_JWT_SECRET);
    const roomId = String(payload.room_id || '').trim();
    if (!roomId) {
      throw new Error('Token missing room_id');
    }

    const status = await fetchRoomStatus(FLASK_INTERNAL_BASE_URL, INTERNAL_API_TOKEN, roomId);
    if (!status.active) {
      throw new Error('Call room is inactive');
    }

    socket.data.roomId = roomId;
    socket.data.participantId = String(payload.sub || `participant-${crypto.randomUUID()}`);
    socket.data.displayName = String(payload.display_name || 'Participant');
    socket.data.ipAddress = ipAddress;
    return next();
  } catch (error) {
    return next(new Error(error.message || 'Unauthorized'));
  }
});

function relayToRoomPeers(socket, eventName, payload) {
  const roomId = socket.data.roomId;
  socket.to(roomId).emit(eventName, payload);
}

async function processSignalEvent(socket, signalType, payload) {
  const rateAllowed = await roomStore.checkRate(
    socket.data.ipAddress,
    'signal',
    SIGNAL_RATE_WINDOW_SECONDS,
    SIGNAL_RATE_LIMIT
  );
  if (!rateAllowed) {
    socket.emit('error:event', { code: 'rate_limit', message: 'Signal rate limit exceeded' });
    return;
  }

  const validated = validateSignalPayload(signalType, payload);
  if (!validated.ok) {
    socket.emit('error:event', { code: 'invalid_payload', message: validated.error });
    return;
  }

  await roomStore.touchParticipant(socket.data.participantId);
  const eventName = signalType === 'chat_text'
    ? 'chat:text'
    : signalType === 'chat_image'
      ? 'chat:image'
      : `signal:${signalType}`;
  relayToRoomPeers(socket, eventName, validated.payload);
}

io.on('connection', async (socket) => {
  const roomId = socket.data.roomId;
  const participantId = socket.data.participantId;

  await socket.join(roomId);
  const participants = await roomStore.addParticipant(roomId, participantId, socket.id, socket.data.ipAddress);
  socket.emit('room:joined', {
    room_id: roomId,
    participant_id: participantId,
    participants,
  });
  socket.to(roomId).emit('participant:joined', {
    participant_id: participantId,
    participants,
  });
  makeLog('participant_joined', { roomId, participantId, participants });

  socket.on('signal:offer', async (payload) => processSignalEvent(socket, 'offer', payload));
  socket.on('signal:answer', async (payload) => processSignalEvent(socket, 'answer', payload));
  socket.on('signal:candidate', async (payload) => processSignalEvent(socket, 'candidate', payload));
  socket.on('signal:hangup', async (payload) => processSignalEvent(socket, 'hangup', payload));
  socket.on('chat:text', async (payload) => processSignalEvent(socket, 'chat_text', payload));
  socket.on('chat:image', async (payload) => processSignalEvent(socket, 'chat_image', payload));

  socket.on('disconnect', async () => {
    const result = await roomStore.removeParticipantBySocket(socket.id);
    if (!result || !result.roomId) {
      return;
    }
    io.to(result.roomId).emit('participant:left', {
      participant_id: result.participantId,
      participants: result.participants,
    });
    makeLog('participant_left', {
      roomId: result.roomId,
      participantId: result.participantId,
      participants: result.participants,
    });
  });
});

server.listen(PORT, () => {
  makeLog('signaling_service_started', {
    port: PORT,
    wsPath: WS_PATH,
    redisUrl: REDIS_URL,
  });
});

async function shutdown(signal) {
  makeLog('shutdown_requested', { signal });
  try {
    await io.close();
    await redis.quit();
  } catch (error) {
    makeLog('shutdown_error', { error: error.message });
  } finally {
    process.exit(0);
  }
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
