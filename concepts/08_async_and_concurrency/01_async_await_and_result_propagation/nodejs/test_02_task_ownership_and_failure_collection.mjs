// 任务所有权、结果复用与失败收集。
// 共同问题：异步结果能否被多个观察者复用；组合失败是否取消其他工作；
// 调用方如何选择快速失败或把失败作为结果收集。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: async_await_and_result_propagation
// polyglot-related: languages/nodejs/language/test_019_async_functions_await_microtasks_and_concurrency.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Promise.allSettled 按输入顺序收集值与失败', async () => {
  const failure = new Error('failed');

  const results = await Promise.allSettled([
    Promise.resolve(1),
    Promise.reject(failure),
  ]);

  assert.deepEqual(results, [
    { status: 'fulfilled', value: 1 },
    { status: 'rejected', reason: failure },
  ]);
});

test('Promise.all 快速拒绝但不会取消其余 Promise 工作', async () => {
  const events = [];
  let finish;
  const remaining = new Promise((resolve) => {
    finish = () => {
      events.push('remaining completed');
      resolve(2);
    };
  });

  await assert.rejects(
    Promise.all([Promise.reject(new Error('failed')), remaining]),
    /failed/,
  );
  assert.deepEqual(events, []);

  finish();
  assert.equal(await remaining, 2);
  assert.deepEqual(events, ['remaining completed']);

  // Promise 表示结果而非工作所有权；组合器的 rejection 不会自动撤销底层操作。
});

test('thenable 由 await 通过 Promise 解析协议同化', async () => {
  const events = [];
  const thenable = {
    then(resolve) {
      events.push('then');
      resolve(42);
    },
  };

  assert.equal(await thenable, 42);
  assert.deepEqual(events, ['then']);
});
