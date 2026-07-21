// polyglot-covers:
// - nodejs.core.worker-message-channel-structured-clone
// - nodejs.core.worker-message-port-start-close-ref-unref-and-has-ref
// - nodejs.core.worker-receive-message-on-port
// - nodejs.core.worker-transfer-message-port
// - nodejs.core.worker-broadcast-channel
// - nodejs.core.worker-post-message-to-thread
// - nodejs.core.process-worker-message-event
// - nodejs.core.worker-lock-manager-exclusive-queue-and-query
// - nodejs.core.worker-lock-manager-if-available
// - nodejs.core.worker-lock-manager-abort-pending-request

import assert from 'node:assert/strict';
import test from 'node:test';

import { once } from 'node:events';
import {
  BroadcastChannel,
  MessageChannel,
  MessagePort,
  Worker,
  locks,
  postMessageToThread,
  receiveMessageOnPort,
  threadId,
} from 'node:worker_threads';

test('MessageChannel 用 structured clone 双向传值，MessagePort 控制事件循环引用', async () => {
  const { port1, port2 } = new MessageChannel();
  assert.equal(port1.hasRef(), false);
  port1.start();
  assert.equal(port1.hasRef(), false);
  port1.ref();
  assert.equal(port1.hasRef(), true);
  port1.unref();
  assert.equal(port1.hasRef(), false);

  const received = once(port2, 'message');
  port1.postMessage({ map: new Map([['answer', 42]]) });
  const [message] = await received;
  assert.ok(message.map instanceof Map);
  assert.equal(message.map.get('answer'), 42);

  const port1Closed = once(port1, 'close');
  const port2Closed = once(port2, 'close');
  port1.close();
  port2.close();
  await Promise.all([port1Closed, port2Closed]);
});

test('receiveMessageOnPort 同步取出队列最旧消息，不触发 message 事件', () => {
  const { port1, port2 } = new MessageChannel();
  try {
    port1.postMessage('first');
    port1.postMessage('second');
    assert.deepEqual(receiveMessageOnPort(port2), { message: 'first' });
    assert.deepEqual(receiveMessageOnPort(port2), { message: 'second' });
    assert.equal(receiveMessageOnPort(port2), undefined);
  } finally {
    port1.close();
    port2.close();
  }
});

test('MessagePort 可作为 transferList 成员移交给 Worker 建立专用通道', async () => {
  const worker = new Worker(`
    const { MessagePort, parentPort } = require('node:worker_threads');
    parentPort.once('message', ({ port }) => {
      parentPort.postMessage(port instanceof MessagePort);
      port.once('message', (value) => {
        port.postMessage('worker:' + value);
        port.close();
      });
    });
  `, { eval: true });
  const { port1, port2 } = new MessageChannel();
  const workerExit = once(worker, 'exit');
  worker.postMessage({ port: port1 }, [port1]);
  assert.deepEqual(await once(worker, 'message'), [true]);

  const reply = once(port2, 'message');
  port2.postMessage('payload');
  assert.deepEqual(await reply, ['worker:payload']);
  port2.close();
  await workerExit;
});

test('BroadcastChannel 向同名的其他实例广播，但发送者不接收自己的消息', async () => {
  const name = `polyglot-broadcast-${process.pid}`;
  const sender = new BroadcastChannel(name);
  const receiver = new BroadcastChannel(name);
  let senderMessages = 0;
  sender.onmessage = () => {
    senderMessages += 1;
  };
  const received = once(receiver, 'message');
  sender.postMessage({ kind: 'announcement' });
  const [event] = await received;

  assert.deepEqual(event.data, { kind: 'announcement' });
  assert.equal(senderMessages, 0);
  sender.unref();
  sender.ref();
  sender.close();
  receiver.close();
});

test('postMessageToThread 按 threadId 发送，目标用 process workerMessage 接收', async () => {
  assert.equal(threadId, 0);
  const worker = new Worker(`
    const process = require('node:process');
    const { parentPort, threadId } = require('node:worker_threads');
    process.on('workerMessage', (value, source) => {
      parentPort.postMessage({ value, source });
    });
    parentPort.once('message', (message) => {
      if (message === 'close') parentPort.close();
    });
    parentPort.postMessage({ ready: true, threadId });
  `, { eval: true });
  const workerExit = once(worker, 'exit');
  const [ready] = await once(worker, 'message');
  assert.equal(ready.threadId, worker.threadId);

  const delivered = once(worker, 'message');
  await postMessageToThread(worker.threadId, { direct: true });
  assert.deepEqual((await delivered)[0], {
    value: { direct: true },
    source: 0,
  });
  await assert.rejects(
    postMessageToThread(threadId, 'self'),
    (error) => error.code === 'ERR_WORKER_MESSAGING_SAME_THREAD',
  );
  worker.postMessage('close');
  assert.deepEqual(await workerExit, [0]);
});

test('LockManager 串行 exclusive 请求，并用 query/ifAvailable 查看竞争状态', async () => {
  const name = `polyglot-lock-${process.pid}`;
  const order = [];
  let enterFirst;
  let releaseFirst;
  const firstEntered = new Promise((resolve) => {
    enterFirst = resolve;
  });
  const firstGate = new Promise((resolve) => {
    releaseFirst = resolve;
  });
  const first = locks.request(name, async (lock) => {
    order.push(`first:${lock.mode}`);
    enterFirst();
    await firstGate;
  });
  await firstEntered;

  const unavailable = await locks.request(
    name,
    { ifAvailable: true },
    (lock) => lock,
  );
  assert.equal(unavailable, null);
  const second = locks.request(name, (lock) => {
    order.push(`second:${lock.mode}`);
  });
  const snapshot = await locks.query();
  assert.ok(snapshot.held.some((lock) => lock.name === name));
  assert.ok(snapshot.pending.some((lock) => lock.name === name));

  releaseFirst();
  await Promise.all([first, second]);
  assert.deepEqual(order, ['first:exclusive', 'second:exclusive']);
});

test('AbortSignal 只取消尚未获得的 lock 请求，不抢占持有者', async () => {
  const name = `polyglot-abort-lock-${process.pid}`;
  let enterHolder;
  let releaseHolder;
  const holderEntered = new Promise((resolve) => {
    enterHolder = resolve;
  });
  const holderGate = new Promise((resolve) => {
    releaseHolder = resolve;
  });
  const holder = locks.request(name, async () => {
    enterHolder();
    await holderGate;
  });
  await holderEntered;

  const controller = new AbortController();
  const reason = new Error('cancel pending lock');
  const pending = locks.request(name, { signal: controller.signal }, () => undefined);
  controller.abort(reason);
  await assert.rejects(
    pending,
    (error) => error === reason,
  );
  // LockManager 按 AbortSignal.reason 原样拒绝；只有未提供 reason 时才使用默认 AbortError。
  assert.ok((await locks.query()).held.some((lock) => lock.name === name));
  releaseHolder();
  await holder;
});
