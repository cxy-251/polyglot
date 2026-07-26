// 异步等待与结果传播。
// 共同问题：异步函数调用何时开始执行；await 如何取得结果；失败如何传播；
// 多个结果如何组合。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/nodejs/language/test_019_async_functions_await_microtasks_and_concurrency.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('async 函数同步执行到首个 await 并立即返回 Promise', async () => {
  const events = [];
  async function work() {
    events.push('start');
    await 0;
    events.push('resume');
    return 42;
  }

  const result = work();
  assert.deepEqual(events, ['start']);
  assert.equal(result instanceof Promise, true);
  assert.equal(await result, 42);
  assert.deepEqual(events, ['start', 'resume']);
});

test('await 返回 fulfilled 值并传播 rejection', async () => {
  assert.equal(await Promise.resolve(42), 42);
  await assert.rejects(async () => {
    await Promise.reject(new Error('failed'));
  }, /failed/);
});

test('Promise.all 保留输入顺序并在首个 rejection 时拒绝', async () => {
  assert.deepEqual(await Promise.all([Promise.resolve(2), Promise.resolve(1)]), [2, 1]);
  await assert.rejects(Promise.all([Promise.resolve(1), Promise.reject(new Error('failed'))]), /failed/);
});

test('Promise 可被多个观察者重复 await', async () => {
  const result = Promise.resolve(42);

  assert.equal(await result, 42);
  assert.equal(await result, 42);
});
