class RoomStore {
  constructor(redisClient, options = {}) {
    this.redis = redisClient;
    this.roomTtlSeconds = Number(options.roomTtlSeconds || 60 * 60 * 3);
    this.participantTtlSeconds = Number(options.participantTtlSeconds || 60 * 5);
  }

  _roomParticipantsKey(roomId) {
    return `vc:room:${roomId}:participants`;
  }

  _roomMetaKey(roomId) {
    return `vc:room:${roomId}:meta`;
  }

  _participantKey(participantId) {
    return `vc:participant:${participantId}`;
  }

  _socketKey(socketId) {
    return `vc:socket:${socketId}`;
  }

  async addParticipant(roomId, participantId, socketId, ipAddress) {
    const now = Date.now().toString();
    const participantsKey = this._roomParticipantsKey(roomId);
    const metaKey = this._roomMetaKey(roomId);
    const participantKey = this._participantKey(participantId);
    const socketKey = this._socketKey(socketId);

    const transaction = this.redis.multi();
    transaction.sadd(participantsKey, participantId);
    transaction.expire(participantsKey, this.roomTtlSeconds);
    transaction.hsetnx(metaKey, 'created_at', now);
    transaction.hset(metaKey, 'updated_at', now);
    transaction.expire(metaKey, this.roomTtlSeconds);
    transaction.hset(participantKey, 'room_id', roomId, 'socket_id', socketId, 'last_seen', now, 'ip_address', ipAddress || 'unknown');
    transaction.expire(participantKey, this.participantTtlSeconds);
    transaction.set(socketKey, participantId, 'EX', this.participantTtlSeconds);
    await transaction.exec();

    const participants = await this.redis.scard(participantsKey);
    await this.redis.hset(metaKey, 'participant_count', String(participants), 'updated_at', Date.now().toString());
    return participants;
  }

  async touchParticipant(participantId) {
    const participantKey = this._participantKey(participantId);
    const now = Date.now().toString();
    await this.redis.hset(participantKey, 'last_seen', now);
    await this.redis.expire(participantKey, this.participantTtlSeconds);
  }

  async removeParticipantBySocket(socketId) {
    const socketKey = this._socketKey(socketId);
    const participantId = await this.redis.get(socketKey);
    if (!participantId) {
      return null;
    }

    const participantKey = this._participantKey(participantId);
    const roomId = await this.redis.hget(participantKey, 'room_id');
    const transaction = this.redis.multi();
    transaction.del(socketKey);
    transaction.del(participantKey);
    if (roomId) {
      transaction.srem(this._roomParticipantsKey(roomId), participantId);
    }
    await transaction.exec();

    if (!roomId) {
      return { roomId: null, participantId, participants: 0 };
    }

    const participantsKey = this._roomParticipantsKey(roomId);
    const metaKey = this._roomMetaKey(roomId);
    const participants = await this.redis.scard(participantsKey);
    if (participants <= 0) {
      await this.redis.del(participantsKey);
      await this.redis.del(metaKey);
    } else {
      await this.redis.hset(metaKey, 'participant_count', String(participants), 'updated_at', Date.now().toString());
      await this.redis.expire(participantsKey, this.roomTtlSeconds);
      await this.redis.expire(metaKey, this.roomTtlSeconds);
    }

    return { roomId, participantId, participants };
  }

  async clearRoom(roomId) {
    const participantsKey = this._roomParticipantsKey(roomId);
    const participantIds = await this.redis.smembers(participantsKey);

    const transaction = this.redis.multi();
    participantIds.forEach((participantId) => {
      transaction.del(this._participantKey(participantId));
    });
    transaction.del(participantsKey);
    transaction.del(this._roomMetaKey(roomId));
    await transaction.exec();
  }

  async checkRate(ipAddress, kind, windowSeconds, maxCount) {
    const address = ipAddress || 'unknown';
    const key = `vc:rate:${address}:${kind}`;
    const count = await this.redis.incr(key);
    if (count === 1) {
      await this.redis.expire(key, Number(windowSeconds || 10));
    }
    return count <= Number(maxCount || 1);
  }
}

module.exports = {
  RoomStore,
};
