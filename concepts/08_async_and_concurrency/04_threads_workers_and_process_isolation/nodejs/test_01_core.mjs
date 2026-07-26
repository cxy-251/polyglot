// 线程、Worker 与进程隔离。
// 共同问题：并发工作运行在哪里；参数如何进入工作单元；调用方如何等待结果；
// 工作单元是否共享对象、地址空间或运行时状态。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/nodejs/language/test_030_shared_array_buffer_atomics_and_memory_coordination.mjs

import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { isMainThread, Worker } from 'node:worker_threads';

function runWorker(source, workerData) {
  const worker = new Worker(source, { eval: true, workerData });
  return once(worker, 'message').then(([message]) => message);
}

test('Worker 在同一进程的独立 JavaScript 线程中运行', async () => {
  const observation = await runWorker(`
    const { parentPort, isMainThread, threadId } = require('node:worker_threads');
    parentPort.postMessage({ isMainThread, threadId, pid: process.pid });
  `);

  assert.equal(isMainThread, true);
  assert.equal(observation.isMainThread, false);
  assert.notEqual(observation.threadId, 0);
  assert.equal(observation.pid, process.pid);
});

test('workerData 经过结构化克隆而不是共享普通对象', async () => {
  const input = { nested: { value: 1 } };
  const result = await runWorker(`
    const { parentPort, workerData } = require('node:worker_threads');
    workerData.nested.value = 42;
    parentPort.postMessage(workerData);
  `, input);

  assert.equal(result.nested.value, 42);
  assert.equal(input.nested.value, 1);
});

test('消息是 Worker 返回结果的显式边界', async () => {
  const result = await runWorker(`
    const { parentPort, workerData } = require('node:worker_threads');
    parentPort.postMessage(workerData + 1);
  `, 41);

  assert.equal(result, 42);
});

test('Worker 不共享调用方的全局对象', async () => {
  globalThis.polyglotMarker = 'main';
  try {
    const marker = await runWorker(`
      const { parentPort } = require('node:worker_threads');
      parentPort.postMessage(globalThis.polyglotMarker);
    `);
    assert.equal(marker, undefined);
  } finally {
    delete globalThis.polyglotMarker;
  }
});
