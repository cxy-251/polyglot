// 超时所有权、底层取消与屏蔽。
// 共同问题：等待超时是否取消底层工作；取消完成前是否等待清理；
// 调用方能否只取消当前等待而保留共享任务。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: cancellation_timeouts_and_cleanup
// polyglot-related: languages/nodejs/node_core/01_modules_and_runtime/
// polyglot-related+: test_034_runtime_globals_web_apis_abort_and_timer_handles.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Promise.race 的超时结果不会取消未接收信号的底层工作', async () => {
  const timeout = Promise.reject(new Error('timeout'));
  let finish;
  const work = new Promise((resolve) => {
    finish = () => resolve(42);
  });

  await assert.rejects(Promise.race([work, timeout]), /timeout/);

  finish();
  assert.equal(await work, 42);

  // race 只选择首个 settled 结果；若工作 API 不接受 AbortSignal，超时包装无法撤销它。
});

test('AbortSignal.any 转发首个取消原因且保持已取消状态', () => {
  const first = new AbortController();
  const second = new AbortController();
  const combined = AbortSignal.any([first.signal, second.signal]);
  const events = [];
  combined.addEventListener('abort', () => events.push(combined.reason), { once: true });

  second.abort('second');
  first.abort('first');

  assert.equal(combined.aborted, true);
  assert.equal(combined.reason, 'second');
  assert.deepEqual(events, ['second']);

  // AbortSignal 是协作广播；是否停止底层操作、何时完成清理仍由接收信号的 API 定义。
});
