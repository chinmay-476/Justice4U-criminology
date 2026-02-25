const jwt = require('jsonwebtoken');

function verifySocketToken(rawToken, secret) {
  const token = typeof rawToken === 'string' ? rawToken.trim() : '';
  if (!token) {
    throw new Error('Missing signaling token');
  }
  if (!secret) {
    throw new Error('Signaling secret is not configured');
  }

  return jwt.verify(token, secret, { algorithms: ['HS256'] });
}

function getClientIp(socket) {
  const forwarded = socket.handshake && socket.handshake.headers && socket.handshake.headers['x-forwarded-for'];
  if (typeof forwarded === 'string' && forwarded.trim()) {
    return forwarded.split(',')[0].trim();
  }
  return socket.handshake.address || 'unknown';
}

module.exports = {
  getClientIp,
  verifySocketToken,
};
