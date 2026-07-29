// 任务调度、微任务与 Future。
// 共同问题：同步代码与调度任务的先后关系；任务何时开始；完成回调何时运行；
// 调度器是否由语言统一规定。
//
// polyglot-family: async_and_concurrency
// polyglot-concept: scheduling_tasks_microtasks_and_futures
// polyglot-related: languages/nodejs/language/test_019_async_functions_await_microtasks_and_concurrency.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Promise reaction 和 queueMicrotask 在当前栈之后运行', async () => {
  const events = [];

  Promise.resolve().then(() => events.push('promise'));
  queueMicrotask(() => events.push('microtask'));
  events.push('sync');
  await Promise.resolve();

  assert.deepEqual(events, ['sync', 'promise', 'microtask']);
});

test('事件循环回调结束后 nextTick 先于 Promise job', async () => {
  const events = await new Promise((resolve) => {
    setImmediate(() => {
      const observed = [];
      process.nextTick(() => observed.push('nextTick'));
      Promise.resolve().then(() => observed.push('promise'));
      setImmediate(() => resolve(observed));
    });
  });

  assert.deepEqual(events, ['nextTick', 'promise']);

  // node:test 的 async 测试体本身由 Promise job 恢复；队列优先级应在事件循环回调边界观察。
});

test('setImmediate 进入后续事件循环阶段', async () => {
  const events = [];

  setImmediate(() => events.push('immediate'));
  queueMicrotask(() => events.push('microtask'));
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(events, ['microtask', 'immediate']);
});

test('Promise 构造器 executor 同步运行', () => {
  const events = [];

  new Promise((resolve) => {
    events.push('executor');
    resolve();
  });
  events.push('after');

  assert.deepEqual(events, ['executor', 'after']);
});

test('已 fulfilled Promise 的后来 reactions 仍异步并按登记顺序运行', async () => {
  const events = [];
  const result = Promise.resolve(42);

  result.then(() => events.push('first'));
  result.then(() => events.push('second'));
  events.push('sync');

  assert.deepEqual(events, ['sync']);
  await result;
  assert.deepEqual(events, ['sync', 'first', 'second']);
});
