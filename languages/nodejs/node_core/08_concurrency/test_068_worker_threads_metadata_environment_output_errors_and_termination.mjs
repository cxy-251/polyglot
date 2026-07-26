// polyglot-covers:
// - nodejs.core.worker-thread-main-thread-parent-port-and-worker-data
// - nodejs.core.worker-thread-id-name-argv-and-resource-limits
// - nodejs.core.worker-online-message-and-exit-order
// - nodejs.core.worker-environment-copy-isolation
// - nodejs.core.worker-share-env
// - nodejs.core.worker-stdout-and-stderr-streams
// - nodejs.core.worker-error-event-and-nonzero-exit
// - nodejs.core.worker-terminate
// - nodejs.core.worker-ref-and-unref

import assert from 'node:assert/strict';
import test from 'node:test';

import { once } from 'node:events';
import {
  SHARE_ENV,
  Worker,
  isInternalThread,
  isMainThread,
  parentPort,
  threadId,
  threadName,
} from 'node:worker_threads';

test('主线程与 Worker 通过默认 MessagePort 交换克隆后的 workerData', async () => {
  assert.equal(isMainThread, true);
  assert.equal(isInternalThread, false);
  assert.equal(parentPort, null);
  assert.equal(threadId, 0);
  assert.equal(threadName, '');

  const worker = new Worker(`
    const {
      isInternalThread,
      isMainThread,
      parentPort,
      threadId,
      threadName,
      workerData,
    } = require('node:worker_threads');
    workerData.nested.value = 99;
    parentPort.postMessage({
      isInternalThread,
      isMainThread,
      hasParentPort: Boolean(parentPort),
      threadId,
      threadName,
      workerData,
      argv: process.argv,
    });
  `, {
    eval: true,
    argv: ['worker-argument'],
    name: 'polyglot-worker',
    workerData: { nested: { value: 1 } },
    resourceLimits: { stackSizeMb: 2 },
  });
  const events = [];
  const requestedLimits = worker.resourceLimits;
  worker.on('online', () => events.push('online'));
  worker.on('message', () => events.push('message'));
  worker.on('exit', () => events.push('exit'));
  const workerExit = once(worker, 'exit');
  const [message] = await once(worker, 'message');
  const [exitCode] = await workerExit;

  assert.equal(message.isInternalThread, false);
  assert.equal(message.isMainThread, false);
  assert.equal(message.hasParentPort, true);
  assert.ok(message.threadId > 0);
  assert.equal(message.threadName, 'polyglot-worker');
  assert.deepEqual(message.workerData, { nested: { value: 99 } });
  assert.ok(message.argv.includes('worker-argument'));
  assert.equal(exitCode, 0);
  assert.deepEqual(events, ['online', 'message', 'exit']);
  assert.equal(worker.threadId, -1);
  assert.equal(requestedLimits.stackSizeMb, 2);
  assert.deepEqual(worker.resourceLimits, {});
  // 退出后 threadId 变成 -1，resourceLimits 也不再保留运行期信息；需要诊断时应提前读取。
  // workerData 使用 structured clone，Worker 的嵌套修改不会回写构造参数对象。
});

test('默认 env 是创建时副本，Worker 修改不会回写 process.env', async () => {
  const key = 'POLYGLOT_WORKER_ENV_COPY';
  const previous = process.env[key];
  try {
    process.env[key] = 'parent value';
    const worker = new Worker(`
      const { parentPort } = require('node:worker_threads');
      const initial = process.env.POLYGLOT_WORKER_ENV_COPY;
      process.env.POLYGLOT_WORKER_ENV_COPY = 'worker value';
      parentPort.postMessage({ initial, changed: process.env.POLYGLOT_WORKER_ENV_COPY });
    `, { eval: true });
    const workerExit = once(worker, 'exit');
    const [message] = await once(worker, 'message');
    await workerExit;

    assert.deepEqual(message, {
      initial: 'parent value',
      changed: 'worker value',
    });
    assert.equal(process.env[key], 'parent value');
  } finally {
    if (previous === undefined) delete process.env[key];
    else process.env[key] = previous;
  }
});

test('SHARE_ENV 共享同一个环境对象，修改后必须由父线程恢复', async () => {
  const key = 'POLYGLOT_WORKER_SHARED_ENV';
  const previous = process.env[key];
  try {
    delete process.env[key];
    const worker = new Worker(`
      const { parentPort } = require('node:worker_threads');
      process.env.POLYGLOT_WORKER_SHARED_ENV = 'set in worker';
      parentPort.postMessage('done');
    `, { eval: true, env: SHARE_ENV });
    const workerExit = once(worker, 'exit');
    await once(worker, 'message');
    await workerExit;
    assert.equal(process.env[key], 'set in worker');
  } finally {
    if (previous === undefined) delete process.env[key];
    else process.env[key] = previous;
  }
});

test('stdout/stderr 选项把 Worker 输出暴露为父线程可读流', async () => {
  const worker = new Worker(`
    console.log('worker stdout');
    console.error('worker stderr');
  `, { eval: true, stdout: true, stderr: true });
  const stdout = [];
  const stderr = [];
  worker.stdout.on('data', (chunk) => stdout.push(chunk));
  worker.stderr.on('data', (chunk) => stderr.push(chunk));
  await once(worker, 'exit');

  assert.equal(Buffer.concat(stdout).toString(), 'worker stdout\n');
  assert.equal(Buffer.concat(stderr).toString(), 'worker stderr\n');
});

test('未捕获异常触发 error，随后 Worker 以退出码 1 结束', async () => {
  const worker = new Worker(`throw new TypeError('worker boom');`, { eval: true });
  const workerError = once(worker, 'error');
  // events.once(worker, 'exit') 会额外监听 error 并拒绝；这里要独立观察 error 与 exit，
  // 否则同一个 Worker error 会成为尚未 await 的拒绝，在 strict 模式下被测试框架报告。
  const workerExit = new Promise((resolve) => worker.once('exit', resolve));
  const [error] = await workerError;
  const exitCode = await workerExit;

  assert.ok(error instanceof TypeError);
  assert.equal(error.message, 'worker boom');
  assert.equal(exitCode, 1);
});

test('terminate 可在任意点停止 Worker，返回退出码 1', async () => {
  const worker = new Worker(`
    const { parentPort } = require('node:worker_threads');
    parentPort.on('message', () => {});
  `, { eval: true });
  await once(worker, 'online');
  assert.equal(worker.unref(), undefined);
  assert.equal(worker.ref(), undefined);
  // ref/unref 只决定该句柄能否独自维持进程；它们不像 MessagePort API 那样返回 this。

  const exitEvent = once(worker, 'exit');
  const terminateCode = await worker.terminate();
  assert.equal(terminateCode, 1);
  assert.deepEqual(await exitEvent, [1]);
  assert.equal(worker.threadId, -1);
});
