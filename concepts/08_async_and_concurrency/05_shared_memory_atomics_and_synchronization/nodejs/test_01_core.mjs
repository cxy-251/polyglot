// 共享内存、原子操作与同步。
// 共同问题：并发工作如何共享状态；互斥和条件通知保证什么；是否提供原子读改写；
// 消息传递与共享内存的边界在哪里。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/nodejs/language/test_030_shared_array_buffer_atomics_and_memory_coordination.mjs

import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { Worker } from 'node:worker_threads';

test('SharedArrayBuffer 的视图观察同一字节存储', () => {
  const storage = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT);
  const first = new Int32Array(storage);
  const second = new Int32Array(storage);

  first[0] = 42;

  assert.equal(second[0], 42);
});

test('Atomics.add 是共享整数上的原子读改写', () => {
  const values = new Int32Array(new SharedArrayBuffer(4));

  assert.equal(Atomics.add(values, 0, 2), 0);
  assert.equal(Atomics.add(values, 0, 3), 2);
  assert.equal(Atomics.load(values, 0), 5);
});

test('Worker 可通过共享存储发布结果', async () => {
  const storage = new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT);
  const worker = new Worker(`
    const { parentPort, workerData } = require('node:worker_threads');
    const value = new Int32Array(workerData);
    Atomics.store(value, 0, 42);
    parentPort.postMessage('stored');
  `, { eval: true, workerData: storage });

  const [[message], [exitCode]] = await Promise.all([
    once(worker, 'message'),
    once(worker, 'exit'),
  ]);

  assert.equal(message, 'stored');
  assert.equal(exitCode, 0);
  assert.equal(Atomics.load(new Int32Array(storage), 0), 42);
});

test('compareExchange 只在观察到预期值时更新', () => {
  const values = new Int32Array(new SharedArrayBuffer(4));
  Atomics.store(values, 0, 1);

  assert.equal(Atomics.compareExchange(values, 0, 0, 9), 1);
  assert.equal(Atomics.load(values, 0), 1);
  assert.equal(Atomics.compareExchange(values, 0, 1, 9), 1);
  assert.equal(Atomics.load(values, 0), 9);

  // Atomics 只接受共享整数视图；普通对象仍通过消息结构化克隆而不是原子访问。
});
