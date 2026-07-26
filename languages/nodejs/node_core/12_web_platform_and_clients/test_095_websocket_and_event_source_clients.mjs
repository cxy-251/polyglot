// polyglot-covers:
// - nodejs.core.web-websocket-http-upgrade-url-protocol-and-ready-state
// - nodejs.core.web-websocket-text-message-send-and-message-event
// - nodejs.core.web-websocket-array-buffer-blob-and-binary-frame-mapping
// - nodejs.core.web-websocket-ping-pong-handled-below-browser-api
// - nodejs.core.web-websocket-close-code-reason-cleanliness-and-close-event
// - nodejs.core.web-websocket-constructor-protocol-validation-and-send-before-open
// - nodejs.core.web-event-source-experimental-flag-and-constructor-state
// - nodejs.core.web-event-source-open-message-custom-event-multiline-data-and-origin
// - nodejs.core.web-event-source-id-retry-reconnect-and-last-event-id
// - nodejs.core.web-event-source-close-stops-reconnection

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import test from 'node:test';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const websocketGUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function onceEvent(target, type) {
  return new Promise((resolve, reject) => {
    const onEvent = (event) => {
      target.removeEventListener('error', onError);
      resolve(event);
    };
    const onError = (event) => {
      target.removeEventListener(type, onEvent);
      reject(event.error ?? new Error(`unexpected ${type} error`));
    };
    target.addEventListener(type, onEvent, { once: true });
    if (type !== 'error') target.addEventListener('error', onError, { once: true });
  });
}

function encodeServerFrame(opcode, data = Buffer.alloc(0)) {
  const payload = Buffer.isBuffer(data) ? data : Buffer.from(data);
  let header;
  if (payload.length < 126) {
    header = Buffer.from([0x80 | opcode, payload.length]);
  } else if (payload.length <= 0xffff) {
    header = Buffer.alloc(4);
    header[0] = 0x80 | opcode;
    header[1] = 126;
    header.writeUInt16BE(payload.length, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x80 | opcode;
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(payload.length), 2);
  }
  return Buffer.concat([header, payload]);
}

function decodeClientFrames(buffer) {
  const frames = [];
  let offset = 0;
  while (buffer.length - offset >= 2) {
    const first = buffer[offset];
    const second = buffer[offset + 1];
    let length = second & 0x7f;
    let headerLength = 2;

    if (length === 126) {
      if (buffer.length - offset < 4) break;
      length = buffer.readUInt16BE(offset + 2);
      headerLength = 4;
    } else if (length === 127) {
      if (buffer.length - offset < 10) break;
      const largeLength = buffer.readBigUInt64BE(offset + 2);
      assert.ok(largeLength <= BigInt(Number.MAX_SAFE_INTEGER));
      length = Number(largeLength);
      headerLength = 10;
    }

    const masked = (second & 0x80) !== 0;
    const maskLength = masked ? 4 : 0;
    const frameLength = headerLength + maskLength + length;
    if (buffer.length - offset < frameLength) break;

    const maskOffset = offset + headerLength;
    const payloadOffset = maskOffset + maskLength;
    const payload = Buffer.from(buffer.subarray(payloadOffset, payloadOffset + length));
    if (masked) {
      const mask = buffer.subarray(maskOffset, maskOffset + 4);
      for (let index = 0; index < payload.length; index += 1) {
        payload[index] ^= mask[index % 4];
      }
    }
    frames.push({
      final: (first & 0x80) !== 0,
      opcode: first & 0x0f,
      masked,
      payload,
    });
    offset += frameLength;
  }
  return { frames, rest: buffer.subarray(offset) };
}

async function createWebSocketFixture() {
  const connectionReady = deferred();
  const sockets = new Set();
  const server = createServer();

  server.on('upgrade', (request, socket, head) => {
    sockets.add(socket);
    socket.once('close', () => sockets.delete(socket));

    const key = request.headers['sec-websocket-key'];
    const accept = createHash('sha1').update(`${key}${websocketGUID}`).digest('base64');
    const requestedProtocols = String(request.headers['sec-websocket-protocol'] ?? '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
    const selectedProtocol = requestedProtocols.includes('learning.v1')
      ? 'learning.v1'
      : undefined;
    const responseHeaders = [
      'HTTP/1.1 101 Switching Protocols',
      'Upgrade: websocket',
      'Connection: Upgrade',
      `Sec-WebSocket-Accept: ${accept}`,
    ];
    if (selectedProtocol !== undefined) {
      responseHeaders.push(`Sec-WebSocket-Protocol: ${selectedProtocol}`);
    }
    socket.write(`${responseHeaders.join('\r\n')}\r\n\r\n`);

    let buffered = head;
    let closeSent = false;
    const frameQueue = [];
    const frameWaiters = [];
    const deliver = (frame) => {
      const waiter = frameWaiters.shift();
      if (waiter === undefined) frameQueue.push(frame);
      else waiter.resolve(frame);
    };
    const consume = (chunk) => {
      buffered = Buffer.concat([buffered, chunk]);
      const decoded = decodeClientFrames(buffered);
      buffered = decoded.rest;
      for (const frame of decoded.frames) {
        deliver(frame);
        if (frame.opcode === 0x08) {
          if (!closeSent) socket.write(encodeServerFrame(0x08, frame.payload));
          socket.end();
        }
      }
    };
    socket.on('data', consume);
    if (head.length > 0) consume(Buffer.alloc(0));

    connectionReady.resolve({
      request,
      selectedProtocol,
      sendText(value) {
        socket.write(encodeServerFrame(0x01, Buffer.from(value)));
      },
      sendBinary(value) {
        socket.write(encodeServerFrame(0x02, Buffer.from(value)));
      },
      sendPing(value) {
        socket.write(encodeServerFrame(0x09, Buffer.from(value)));
      },
      sendClose(code, reason) {
        const payload = Buffer.alloc(2 + Buffer.byteLength(reason));
        payload.writeUInt16BE(code, 0);
        payload.write(reason, 2);
        closeSent = true;
        socket.write(encodeServerFrame(0x08, payload));
      },
      nextFrame() {
        if (frameQueue.length > 0) return Promise.resolve(frameQueue.shift());
        const next = deferred();
        frameWaiters.push(next);
        return next.promise;
      },
    });
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, 'object');

  return {
    url: `ws://127.0.0.1:${address.port}/socket?lesson=1`,
    connection: connectionReady.promise,
    async close() {
      for (const socket of sockets) socket.destroy();
      await new Promise((resolve, reject) => {
        server.close((error) => error === undefined ? resolve() : reject(error));
      });
    },
  };
}

test('WebSocket 通过 HTTP Upgrade 协商子协议并双向传递文本消息', async () => {
  const fixture = await createWebSocketFixture();
  const socket = new WebSocket(fixture.url, ['learning.v1', 'fallback.v1']);
  try {
    assert.equal(socket.readyState, WebSocket.CONNECTING);
    const openEvent = await onceEvent(socket, 'open');
    const serverConnection = await fixture.connection;

    assert.ok(openEvent instanceof Event);
    assert.equal(socket.readyState, WebSocket.OPEN);
    assert.equal(socket.url, fixture.url);
    assert.equal(socket.protocol, 'learning.v1');
    assert.equal(socket.extensions, '');
    assert.equal(serverConnection.selectedProtocol, 'learning.v1');
    assert.equal(serverConnection.request.url, '/socket?lesson=1');
    assert.match(serverConnection.request.headers.upgrade, /^websocket$/i);

    const incomingMessage = onceEvent(socket, 'message');
    serverConnection.sendText('server says hello');
    const message = await incomingMessage;
    assert.ok(message instanceof MessageEvent);
    assert.equal(message.data, 'server says hello');
    assert.equal(message.origin, `ws://127.0.0.1:${new URL(fixture.url).port}`);

    socket.send('client says hello');
    const sentFrame = await serverConnection.nextFrame();
    assert.deepEqual(
      { final: sentFrame.final, opcode: sentFrame.opcode, masked: sentFrame.masked },
      { final: true, opcode: 0x01, masked: true },
    );
    assert.equal(sentFrame.payload.toString(), 'client says hello');

    const closeEventPromise = onceEvent(socket, 'close');
    socket.close(1000, 'lesson complete');
    assert.equal(socket.readyState, WebSocket.CLOSING);
    const closeFrame = await serverConnection.nextFrame();
    assert.equal(closeFrame.opcode, 0x08);
    const closeEvent = await closeEventPromise;
    assert.equal(closeEvent.code, 1000);
    assert.equal(closeEvent.reason, 'lesson complete');
    assert.equal(closeEvent.wasClean, true);
    assert.equal(socket.readyState, WebSocket.CLOSED);
  } finally {
    if (socket.readyState !== WebSocket.CLOSED) socket.close();
    await fixture.close();
  }
  // 浏览器式 API 只暴露消息；HTTP Upgrade、客户端掩码和帧 opcode
  // 由实现处理。
});

test('WebSocket 二进制品牌与协议级 ping/pong', async () => {
  const fixture = await createWebSocketFixture();
  const socket = new WebSocket(fixture.url);
  try {
    socket.binaryType = 'arraybuffer';
    await onceEvent(socket, 'open');
    const serverConnection = await fixture.connection;

    const binaryMessage = onceEvent(socket, 'message');
    serverConnection.sendBinary([0, 127, 255]);
    const received = await binaryMessage;
    assert.ok(received.data instanceof ArrayBuffer);
    assert.deepEqual([...new Uint8Array(received.data)], [0, 127, 255]);

    socket.send(new Uint8Array([1, 2, 3]));
    const binaryFrame = await serverConnection.nextFrame();
    assert.equal(binaryFrame.opcode, 0x02);
    assert.deepEqual([...binaryFrame.payload], [1, 2, 3]);

    serverConnection.sendPing('health');
    const pong = await serverConnection.nextFrame();
    assert.equal(pong.opcode, 0x0a);
    assert.equal(pong.payload.toString(), 'health');

    const closeEventPromise = onceEvent(socket, 'close');
    serverConnection.sendClose(4001, 'server shutdown');
    const closeReply = await serverConnection.nextFrame();
    assert.equal(closeReply.opcode, 0x08);
    const closeEvent = await closeEventPromise;
    assert.ok(closeEvent instanceof CloseEvent);
    assert.equal(closeEvent.code, 4001);
    assert.equal(closeEvent.reason, 'server shutdown');
    assert.equal(closeEvent.wasClean, true);
  } finally {
    if (socket.readyState !== WebSocket.CLOSED) socket.close();
    await fixture.close();
  }
});

test('WebSocket 在构造时校验 URL/子协议，在 OPEN 前禁止 send', async () => {
  assert.throws(
    () => new WebSocket('ftp://127.0.0.1/not-websocket'),
    { name: 'SyntaxError' },
  );
  assert.throws(
    () => new WebSocket('ws://127.0.0.1/', ['duplicate', 'duplicate']),
    { name: 'SyntaxError' },
  );
  assert.throws(
    () => new WebSocket('ws://127.0.0.1/', ['contains space']),
    { name: 'SyntaxError' },
  );

  const fixture = await createWebSocketFixture();
  const socket = new WebSocket(fixture.url);
  try {
    assert.throws(() => socket.send('too early'), {
      name: 'InvalidStateError',
    });
    await onceEvent(socket, 'open');
    await fixture.connection;
    assert.throws(() => socket.close(1005), { name: 'InvalidAccessError' });
    assert.throws(
      () => socket.close(1000, '汉'.repeat(42)),
      { name: 'SyntaxError' },
    );

    const closePromise = onceEvent(socket, 'close');
    socket.close();
    await closePromise;
  } finally {
    if (socket.readyState !== WebSocket.CLOSED) socket.close();
    await fixture.close();
  }
  // close reason 上限是 123 个 UTF-8 字节，不是 123 个 JavaScript 字符。
});

test('CloseEvent 独立保存协议关闭信息，不等同于普通 Event', () => {
  const event = new CloseEvent('close', {
    code: 1000,
    reason: 'normal',
    wasClean: true,
  });
  assert.ok(event instanceof Event);
  assert.equal(event.type, 'close');
  assert.equal(event.code, 1000);
  assert.equal(event.reason, 'normal');
  assert.equal(event.wasClean, true);
});

async function createEventSourceServer() {
  const requests = [];
  const server = createServer((request, response) => {
    requests.push({
      accept: request.headers.accept,
      lastEventId: request.headers['last-event-id'],
    });
    response.writeHead(200, {
      'cache-control': 'no-cache',
      'content-type': 'text/event-stream',
    });

    if (requests.length === 1) {
      response.end([
        ': comment is ignored',
        'retry: 1',
        'id: lesson-1',
        'event: lesson',
        'data: first line',
        'data: second line',
        '',
        '',
      ].join('\n'));
      return;
    }

    response.end([
      'id: lesson-2',
      'data: reconnected',
      '',
      '',
    ].join('\n'));
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, 'object');
  return {
    url: `http://127.0.0.1:${address.port}/events`,
    requests,
    close: () => new Promise((resolve, reject) => {
      server.close((error) => error === undefined ? resolve() : reject(error));
    }),
  };
}

test('EventSource 需实验开关，并解析自定义事件、续传 ID 与重连', async () => {
  assert.equal(typeof globalThis.EventSource, 'undefined');
  const fixture = await createEventSourceServer();
  const childSource = `
    const records = [];
    const keepAlive = new MessageChannel();
    keepAlive.port1.onmessage = () => {};
    const source = new EventSource(${JSON.stringify('EVENT_SOURCE_URL')}, {
      withCredentials: true,
    });
    records.push({
      initialState: source.readyState,
      url: source.url,
      withCredentials: source.withCredentials,
    });
    source.addEventListener('open', () => records.push({ type: 'open' }));
    source.addEventListener('lesson', (event) => {
      records.push({
        type: event.type,
        data: event.data,
        lastEventId: event.lastEventId,
        origin: event.origin,
      });
    });
    await new Promise((resolve) => {
      source.addEventListener('message', (event) => {
        records.push({
          type: event.type,
          data: event.data,
          lastEventId: event.lastEventId,
          origin: event.origin,
        });
        source.close();
        keepAlive.port1.close();
        keepAlive.port2.close();
        records.push({ finalState: source.readyState });
        resolve();
      });
    });
    process.stdout.write(JSON.stringify(records));
  `.replace('EVENT_SOURCE_URL', fixture.url);

  try {
    const { stdout, stderr } = await execFileAsync(process.execPath, [
      '--experimental-eventsource',
      '--input-type=module',
      '--eval',
      childSource,
    ], { encoding: 'utf8' });
    const records = JSON.parse(stdout);
    assert.deepEqual(records[0], {
      initialState: 0,
      url: fixture.url,
      withCredentials: true,
    });
    assert.deepEqual(records.slice(1).map(({ type, data, lastEventId }) => ({
      type,
      data,
      lastEventId,
    })), [
      { type: 'open', data: undefined, lastEventId: undefined },
      { type: 'lesson', data: 'first line\nsecond line', lastEventId: 'lesson-1' },
      { type: 'open', data: undefined, lastEventId: undefined },
      { type: 'message', data: 'reconnected', lastEventId: 'lesson-2' },
      { type: undefined, data: undefined, lastEventId: undefined },
    ]);
    assert.equal(records[2].origin, new URL(fixture.url).origin);
    assert.equal(records[4].origin, new URL(fixture.url).origin);
    assert.deepEqual(records.at(-1), { finalState: 2 });
    assert.match(stderr, /Warning: EventSource is experimental/);

    assert.deepEqual(fixture.requests, [
      { accept: 'text/event-stream', lastEventId: undefined },
      { accept: 'text/event-stream', lastEventId: 'lesson-1' },
    ]);
  } finally {
    await fixture.close();
  }
  // 服务端断流后 readyState 会进入 CONNECTING；retry 控制重试间隔，id
  // 会进入下一次 Last-Event-ID 请求头。显式 close() 后变为 CLOSED，并
  // 终止后续重连。
});
