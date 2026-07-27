// ready queue、完成回调与显式执行边界。
// 共同问题：已经完成的结果何时通知后来观察者；同一队列是否保持登记顺序；
// 创建结果对象是否等同于启动工作。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/nodejs/language/test_019_async_functions_await_microtasks_and_concurrency.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('已 fulfilled Promise 的后来 reaction 仍异步排入 job queue', async () => {
  const events = [];
  const result = Promise.resolve(42);

  result.then(() => events.push('reaction'));
  events.push('sync');

  assert.deepEqual(events, ['sync']);
  await Promise.resolve();
  assert.deepEqual(events, ['sync', 'reaction']);
});

test('同一 Promise 的 reactions 按登记顺序执行', async () => {
  const events = [];
  const result = Promise.resolve();

  result.then(() => events.push('first'));
  result.then(() => events.push('second'));
  await result;
  await Promise.resolve();

  assert.deepEqual(events, ['first', 'second']);
});

test('Promise 构造器启动 executor，但 reaction 等待当前栈结束', async () => {
  const events = [];
  const result = new Promise((resolve) => {
    events.push('executor');
    resolve(42);
  });
  result.then(() => events.push('reaction'));
  events.push('sync');

  assert.deepEqual(events, ['executor', 'sync']);
  await result;
  await Promise.resolve();
  assert.deepEqual(events, ['executor', 'sync', 'reaction']);
});
