// polyglot-covers:
// - nodejs.core.dgram-udp-bind-dynamic-loopback-port
// - nodejs.core.dgram-send-buffer-list-and-message-metadata
// - nodejs.core.dgram-connected-mode-send-and-remote-address
// - nodejs.core.dgram-disconnect
// - nodejs.core.dgram-send-and-receive-buffer-size
// - nodejs.core.dgram-reference-lifecycle
// - nodejs.core.dgram-send-queue-introspection
// - nodejs.core.dgram-abort-signal-and-close
// - nodejs.core.dgram-symbol-async-dispose

import assert from 'node:assert/strict';
import test from 'node:test';

import dgram from 'node:dgram';
import { once } from 'node:events';

async function bind(socket) {
  socket.bind(0, '127.0.0.1');
  await once(socket, 'listening');
  return socket.address();
}

async function close(socket) {
  if (!socket) return;
  await socket[Symbol.asyncDispose]();
}

function send(socket, message, port, address) {
  return new Promise((resolve, reject) => {
    const callback = (error, bytes) => {
      if (error) reject(error);
      else resolve(bytes);
    };
    if (port === undefined) socket.send(message, callback);
    else socket.send(message, port, address, callback);
  });
}

test('未连接 UDP socket 可向动态回环端口发送 Buffer 列表', async () => {
  const receiver = dgram.createSocket('udp4');
  const sender = dgram.createSocket('udp4');
  try {
    const address = await bind(receiver);
    const received = once(receiver, 'message');
    const bytes = await send(
      sender,
      [Buffer.from('hello '), Buffer.from('udp')],
      address.port,
      address.address,
    );
    const [message, remote] = await received;

    assert.equal(bytes, 9);
    assert.equal(message.toString(), 'hello udp');
    assert.equal(remote.address, '127.0.0.1');
    assert.equal(remote.family, 'IPv4');
    assert.equal(remote.size, 9);
    assert.equal(typeof remote.port, 'number');
    assert.equal(sender.address().family, 'IPv4');
    assert.equal(sender.getSendQueueSize(), 0);
    assert.equal(sender.getSendQueueCount(), 0);
  } finally {
    await close(sender);
    await close(receiver);
  }
});

test('connect 固定 UDP 对端，send 可省略地址且只接收该对端数据', async () => {
  const receiver = dgram.createSocket('udp4');
  const sender = dgram.createSocket('udp4');
  try {
    const address = await bind(receiver);
    receiver.on('message', (message, remote) => {
      receiver.send(`ack:${message}`, remote.port, remote.address);
    });

    sender.connect(address.port, address.address);
    await once(sender, 'connect');
    assert.deepEqual(sender.remoteAddress(), {
      address: '127.0.0.1',
      family: 'IPv4',
      port: address.port,
    });

    const reply = once(sender, 'message');
    assert.equal(await send(sender, 'ping'), 4);
    assert.equal((await reply)[0].toString(), 'ack:ping');

    sender.disconnect();
    assert.throws(
      () => sender.remoteAddress(),
      (error) => error.code === 'ERR_SOCKET_DGRAM_NOT_CONNECTED',
    );
  } finally {
    await close(sender);
    await close(receiver);
  }
});

test('已 bind 的 socket 可调整内核缓冲区，并显式控制事件循环引用', async () => {
  const socket = dgram.createSocket({ type: 'udp4', reuseAddr: true });
  try {
    await bind(socket);
    socket.setRecvBufferSize(64 * 1024);
    socket.setSendBufferSize(64 * 1024);

    // 内核可能向上取整或施加系统上下限，因此只验证有效容量而不锁定精确值。
    assert.ok(socket.getRecvBufferSize() > 0);
    assert.ok(socket.getSendBufferSize() > 0);
    // dgram.Socket 提供 ref/unref 链式方法，但不像 Timer 那样提供 hasRef 查询。
    assert.equal(socket.unref(), socket);
    assert.equal(socket.ref(), socket);
  } finally {
    await close(socket);
  }
});

test('createSocket 的 AbortSignal 在 abort 时关闭已绑定 socket', async () => {
  const controller = new AbortController();
  const socket = dgram.createSocket({
    type: 'udp4',
    signal: controller.signal,
  });
  const errors = [];
  socket.on('error', (error) => errors.push(error));
  const closed = once(socket, 'close');
  await bind(socket);

  controller.abort(new Error('stop receiving'));
  await closed;
  assert.equal(errors.length, 0);
  assert.throws(
    () => socket.address(),
    (error) => error.code === 'ERR_SOCKET_DGRAM_NOT_RUNNING',
  );
});
