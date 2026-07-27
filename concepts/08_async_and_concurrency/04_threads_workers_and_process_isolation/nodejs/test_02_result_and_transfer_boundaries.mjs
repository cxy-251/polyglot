// 并发结果、异常与数据传输边界。
// 共同问题：工作单元失败如何回到调用方；普通对象是共享、复制还是序列化；
// 所有者如何确认工作单元已经结束。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/nodejs/node_core/08_concurrency/
// polyglot-related+: test_068_worker_threads_metadata_environment_output_errors_and_termination.mjs

import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { Worker } from 'node:worker_threads';

test('transferList 移交 ArrayBuffer 所有权并分离调用方存储', async () => {
  const storage = new ArrayBuffer(4);
  new Uint8Array(storage)[0] = 9;
  const worker = new Worker(`
    const { parentPort, workerData } = require('node:worker_threads');
    parentPort.postMessage(new Uint8Array(workerData)[0]);
  `, {
    eval: true,
    workerData: storage,
    transferList: [storage],
  });
  const [[value], [exitCode]] = await Promise.all([
    once(worker, 'message'),
    once(worker, 'exit'),
  ]);

  assert.equal(value, 9);
  assert.equal(exitCode, 0);
  assert.equal(storage.byteLength, 0);
});

test('Worker 未处理异常通过 error 事件和非零 exit 报告', async () => {
  const worker = new Worker("throw new Error('worker failed');", { eval: true });
  const errorPromise = once(worker, 'error');
  const exitPromise = new Promise((resolve) => worker.once('exit', resolve));

  const [error] = await errorPromise;
  const exitCode = await exitPromise;

  assert.match(error.message, /worker failed/);
  assert.notEqual(exitCode, 0);

  // Worker 异常不会在主线程同步 throw；所有者必须观察 error/exit 或封装为 Promise。
});
