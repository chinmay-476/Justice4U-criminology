function buildStatusUrl(baseUrl, roomId) {
  const safeBase = String(baseUrl || '').replace(/\/+$/, '');
  return `${safeBase}/internal/video-call/${encodeURIComponent(roomId)}/status`;
}

async function fetchRoomStatus(baseUrl, internalToken, roomId) {
  if (!baseUrl || !internalToken || !roomId) {
    return { active: false, case_no: null, ended_at: null };
  }

  try {
    const response = await fetch(buildStatusUrl(baseUrl, roomId), {
      method: 'GET',
      headers: {
        'X-Internal-Token': internalToken,
      },
    });
    if (!response.ok) {
      return { active: false, case_no: null, ended_at: null };
    }
    return await response.json();
  } catch (error) {
    return { active: false, case_no: null, ended_at: null };
  }
}

module.exports = {
  fetchRoomStatus,
};
