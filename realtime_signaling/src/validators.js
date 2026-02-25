const MAX_CHAT_TEXT_LENGTH = 1000;
const MAX_CHAT_IMAGE_DATA_LENGTH = 2_000_000;

function normalizePayload(value) {
  if (!value || typeof value !== 'object') {
    return {};
  }
  return value;
}

function validateSignalPayload(signalType, payload) {
  const body = normalizePayload(payload);

  if (signalType === 'chat_text') {
    const message = String(body.message || '').trim();
    if (!message) {
      return { ok: false, error: 'Message is empty' };
    }
    if (message.length > MAX_CHAT_TEXT_LENGTH) {
      return { ok: false, error: 'Message is too long' };
    }
    return { ok: true, payload: { message } };
  }

  if (signalType === 'chat_image') {
    const imageData = String(body.image_data || '').trim();
    if (!imageData.startsWith('data:image/')) {
      return { ok: false, error: 'Invalid image payload' };
    }
    if (imageData.length > MAX_CHAT_IMAGE_DATA_LENGTH) {
      return { ok: false, error: 'Image is too large' };
    }
    return { ok: true, payload: { image_data: imageData } };
  }

  if (signalType === 'offer' || signalType === 'answer') {
    if (!body || typeof body.sdp !== 'string' || typeof body.type !== 'string') {
      return { ok: false, error: `Invalid ${signalType} payload` };
    }
    return { ok: true, payload: { sdp: body.sdp, type: body.type } };
  }

  if (signalType === 'candidate') {
    if (!body || typeof body.candidate !== 'string') {
      return { ok: false, error: 'Invalid candidate payload' };
    }
    return {
      ok: true,
      payload: {
        candidate: body.candidate,
        sdpMid: body.sdpMid ?? null,
        sdpMLineIndex: body.sdpMLineIndex ?? null,
      },
    };
  }

  if (signalType === 'hangup') {
    return { ok: true, payload: {} };
  }

  return { ok: false, error: 'Unsupported signal type' };
}

module.exports = {
  validateSignalPayload,
};
