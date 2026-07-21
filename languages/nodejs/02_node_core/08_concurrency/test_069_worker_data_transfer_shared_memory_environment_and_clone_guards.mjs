// polyglot-covers:
// - nodejs.core.worker-transfer-list-detaches-array-buffer
// - nodejs.core.worker-shared-array-buffer-and-atomics-across-threads
// - nodejs.core.worker-set-and-get-environment-data
// - nodejs.core.worker-environment-data-clone-per-worker
// - nodejs.core.worker-mark-as-untransferable
// - nodejs.core.worker-is-marked-as-untransferable
// - nodejs.core.worker-mark-as-uncloneable
// - nodejs.core.worker-data-clone-error

import assert from 'node:assert/strict';
import test from 'node:test';

import { once } from 'node:events';
import {
  MessageChannel,
  Worker,
  getEnvironmentData,
  isMarkedAsUntransferable,
  markAsUncloneable,
  markAsUntransferable,
  setEnvironmentData,
} from 'node:worker_threads';

test('transferList 移交 ArrayBuffer 所有权，发送方视图立即 detached', async () => {
  const buffer = new ArrayBuffer(4);
  new Uint8Array(buffer).set([10, 20, 30, 40]);
  const worker = new Worker(`
    const { parentPort, workerData } = require('node:worker_threads');
    const bytes = new Uint8Array(workerData);
    parentPort.postMessage({ sum: bytes.reduce((a, b) => a + b, 0), buffer: workerData }, [
      workerData,
    ]);
  `, {
    eval: true,
    workerData: buffer,
    transferList: [buffer],
  });

  assert.equal(buffer.byteLength, 0);
  const workerExit = once(worker, 'exit');
  const [message] = await once(worker, 'message');
  await workerExit;
  assert.equal(message.sum, 100);
  assert.deepEqual([...new Uint8Array(message.buffer)], [10, 20, 30, 40]);
});

test('SharedArrayBuffer 不转移所有权，Atomics 建立跨线程可见性', async () => {
  const shared = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * 2);
  const values = new Int32Array(shared);
  values[0] = 40;
  const worker = new Worker(`
    const { parentPort, workerData } = require('node:worker_threads');
    const values = new Int32Array(workerData);
    const previous = Atomics.add(values, 0, 2);
    Atomics.store(values, 1, 1);
    Atomics.notify(values, 1);
    parentPort.postMessage(previous);
  `, { eval: true, workerData: shared });
  const waitResult = Atomics.waitAsync(values, 1, 0);
  assert.equal(waitResult.async, true);
  const workerExit = once(worker, 'exit');
  const [previous] = await once(worker, 'message');
  assert.equal(await waitResult.value, 'ok');
  await workerExit;

  assert.equal(previous, 40);
  assert.equal(Atomics.load(values, 0), 42);
  assert.equal(Atomics.load(values, 1), 1);
  assert.equal(shared.byteLength, 8);
});

test('environmentData 自动克隆给新 Worker，每个线程拿到独立副本', async () => {
  const key = 'polyglot-worker-environment-data';
  const previous = getEnvironmentData(key);
  try {
    setEnvironmentData(key, { nested: { count: 1 } });
    const worker = new Worker(`
      const { getEnvironmentData, parentPort } = require('node:worker_threads');
      const value = getEnvironmentData('polyglot-worker-environment-data');
      value.nested.count = 2;
      parentPort.postMessage(value);
    `, { eval: true });
    const workerExit = once(worker, 'exit');
    const [workerValue] = await once(worker, 'message');
    await workerExit;

    assert.deepEqual(workerValue, { nested: { count: 2 } });
    assert.deepEqual(getEnvironmentData(key), { nested: { count: 1 } });
  } finally {
    setEnvironmentData(key, previous);
  }
});

test('markAsUntransferable 禁止所有权转移，但对象仍可被普通克隆', async () => {
  const buffer = new ArrayBuffer(8);
  new Uint8Array(buffer)[0] = 7;
  markAsUntransferable(buffer);
  assert.equal(isMarkedAsUntransferable(buffer), true);

  const { port1, port2 } = new MessageChannel();
  assert.throws(
    () => port1.postMessage(buffer, [buffer]),
    (error) => error.name === 'DataCloneError',
  );
  assert.equal(buffer.byteLength, 8);

  const received = once(port2, 'message');
  port1.postMessage(buffer);
  const [clone] = await received;
  assert.notEqual(clone, buffer);
  assert.equal(new Uint8Array(clone)[0], 7);
  port1.close();
  port2.close();
});

test('markAsUncloneable 让敏感对象无法跨线程复制', () => {
  const value = { secret: 'main-thread-only' };
  markAsUncloneable(value);
  const { port1, port2 } = new MessageChannel();
  try {
    assert.throws(
      () => port1.postMessage(value),
      (error) => error.name === 'DataCloneError',
    );
    assert.deepEqual(value, { secret: 'main-thread-only' });
  } finally {
    port1.close();
    port2.close();
  }
});
