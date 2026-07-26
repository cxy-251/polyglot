// 取消、超时与清理。
// 共同问题：取消是否会强制停止工作；超时如何报告；被取消路径是否仍执行清理；
// 取消由运行时、协作协议还是所有权机制触发。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/nodejs/language/test_019_async_functions_await_microtasks_and_concurrency.mjs

import assert from 'node:assert/strict';
import test from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';

test('AbortController 同步广播协作取消请求', () => {
  const controller = new AbortController();
  const events = [];
  controller.signal.addEventListener('abort', () => events.push('abort'), { once: true });

  controller.abort('stop');

  assert.equal(controller.signal.aborted, true);
  assert.equal(controller.signal.reason, 'stop');
  assert.deepEqual(events, ['abort']);
});

test('支持 AbortSignal 的标准 API 以 AbortError 拒绝', async () => {
  const controller = new AbortController();
  controller.abort();

  await assert.rejects(delay(1000, 'late', { signal: controller.signal }), {
    name: 'AbortError',
  });
});

test('取消导致的 rejection 仍经过 finally 清理', async () => {
  const controller = new AbortController();
  controller.abort();
  const events = [];

  try {
    await delay(1000, undefined, { signal: controller.signal });
  } catch (error) {
    events.push(error.name);
  } finally {
    events.push('cleanup');
  }

  assert.deepEqual(events, ['AbortError', 'cleanup']);
});

test('Promise 本身没有强制取消协议', async () => {
  const result = Promise.resolve(42);

  assert.equal('cancel' in result, false);
  assert.equal(await result, 42);

  // AbortSignal 只是调用方与 API 约定的协作信号，不会自动撤销任意 Promise 中的工作。
});
