// 丢失更新、条件谓词与同步边界。
// 共同问题：运行时锁是否自动保护复合操作；条件通知能否替代状态谓词；
// 发布数据需要哪一个明确同步点。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: shared_memory_atomics_and_synchronization
// polyglot-related: languages/nodejs/language/test_030_shared_array_buffer_atomics_and_memory_coordination.mjs

import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { Worker } from 'node:worker_threads';

test('Atomics.wait 和 notify 以共享整数状态发布 payload', async () => {
  const storage = new SharedArrayBuffer(2 * Int32Array.BYTES_PER_ELEMENT);
  const values = new Int32Array(storage);
  const worker = new Worker(`
    const { parentPort, workerData } = require('node:worker_threads');
    const values = new Int32Array(workerData);
    parentPort.postMessage('ready');
    Atomics.wait(values, 0, 0);
    parentPort.postMessage(Atomics.load(values, 1));
  `, { eval: true, workerData: storage });
  const exitPromise = once(worker, 'exit');

  assert.deepEqual(await once(worker, 'message'), ['ready']);
  const resultPromise = once(worker, 'message');
  Atomics.store(values, 1, 42);
  Atomics.store(values, 0, 1);
  Atomics.notify(values, 0, 1);

  assert.deepEqual(await resultPromise, [42]);
  assert.deepEqual(await exitPromise, [0]);

  // 即使 notify 早于 Worker 真正阻塞，wait 也会因状态不再等于 0 返回；状态谓词而非
  // 通知本身防止丢失唤醒。
});

test('Atomics 拒绝非整数 TypedArray', () => {
  const floating = new Float64Array(new SharedArrayBuffer(8));

  assert.throws(() => Atomics.add(floating, 0, 1), TypeError);

  // Atomics 只定义在共享整数/BigInt 视图上；普通对象与浮点视图没有隐式原子化。
});
