const test = require('node:test');
const assert = require('node:assert/strict');

const { validateSignalPayload } = require('../src/validators');

test('valid chat text payload', () => {
  const result = validateSignalPayload('chat_text', { message: 'hello' });
  assert.equal(result.ok, true);
  assert.equal(result.payload.message, 'hello');
});

test('invalid empty chat text payload', () => {
  const result = validateSignalPayload('chat_text', { message: '   ' });
  assert.equal(result.ok, false);
});

test('valid candidate payload', () => {
  const result = validateSignalPayload('candidate', {
    candidate: 'candidate:0 1 UDP 2122252543 192.168.1.2 12345 typ host',
    sdpMid: '0',
    sdpMLineIndex: 0,
  });
  assert.equal(result.ok, true);
});
