// polyglot-covers:
// - nodejs.language.async-function-return-and-rejection
// - nodejs.language.await-promise-assimilation
// - nodejs.language.await-always-suspends
// - nodejs.language.microtask-queue-order
// - nodejs.language.queue-microtask
// - nodejs.language.sequential-versus-concurrent-await
// - nodejs.language.async-error-handling
// - nodejs.language.async-function-expression-and-method

import assert from 'node:assert/strict';
import test from 'node:test';

test('async 函数总是返回新的 Promise', async () => {
  async function value() {
    return 7;
  }
  async function failure() {
    throw new TypeError('invalid');
  }

  const result = value();
  assert.equal(result instanceof Promise, true);
  assert.equal(await result, 7);
  await assert.rejects(failure(), TypeError);

  const original = Promise.resolve(9);
  async function returnPromise() {
    return original;
  }
  assert.notEqual(returnPromise(), original);
  assert.equal(await returnPromise(), 9);
});

test('await 接受普通值、Promise 和 thenable', async () => {
  const thenable = {
    then(resolve) {
      resolve('thenable value');
    },
  };

  assert.equal(await 1, 1);
  assert.equal(await Promise.resolve(2), 2);
  assert.equal(await thenable, 'thenable value');
});

test('即使 await 普通值，后续代码也会在微任务中恢复', async () => {
  const events = [];

  async function work() {
    events.push('before await');
    await 0;
    events.push('after await');
  }

  const pending = work();
  events.push('caller continues');
  assert.deepEqual(events, ['before await', 'caller continues']);

  await pending;
  assert.deepEqual(events, ['before await', 'caller continues', 'after await']);
});

test('Promise reaction 与 queueMicrotask 按入队顺序运行', async () => {
  const events = [];

  Promise.resolve().then(() => events.push('promise:first'));
  queueMicrotask(() => events.push('queueMicrotask'));
  Promise.resolve().then(() => events.push('promise:last'));
  events.push('synchronous');

  assert.deepEqual(events, ['synchronous']);
  await Promise.resolve();
  assert.deepEqual(events, [
    'synchronous',
    'promise:first',
    'queueMicrotask',
    'promise:last',
  ]);
});

test('微任务中加入的新微任务排到当前队列末尾', async () => {
  const events = [];

  queueMicrotask(() => {
    events.push('first');
    queueMicrotask(() => events.push('nested'));
  });
  queueMicrotask(() => events.push('second'));

  await Promise.resolve();
  assert.deepEqual(events, ['first', 'second']);
  await Promise.resolve();
  assert.deepEqual(events, ['first', 'second', 'nested']);
});

test('顺序 await 与先创建任务再统一等待表达不同依赖关系', async () => {
  const events = [];
  const operation = async (label) => {
    events.push(`start:${label}`);
    await Promise.resolve();
    events.push(`finish:${label}`);
    return label;
  };

  const first = await operation('first');
  const second = await operation('second');
  assert.deepEqual([first, second], ['first', 'second']);
  assert.deepEqual(events, [
    'start:first',
    'finish:first',
    'start:second',
    'finish:second',
  ]);

  events.length = 0;
  const firstPending = operation('first');
  const secondPending = operation('second');
  assert.deepEqual(await Promise.all([firstPending, secondPending]), ['first', 'second']);
  assert.deepEqual(events, [
    'start:first',
    'start:second',
    'finish:first',
    'finish:second',
  ]);
});

test('try/catch 可捕获 await 到的拒绝，但必须在 await 所在范围内', async () => {
  const failure = async () => {
    throw new Error('failed');
  };

  async function handled() {
    try {
      await failure();
      return 'unreachable';
    } catch (error) {
      return `caught:${error.message}`;
    }
  }
  assert.equal(await handled(), 'caught:failed');

  function notHandledHere() {
    try {
      return failure();
    } catch {
      return Promise.resolve('unreachable');
    }
  }
  await assert.rejects(notHandledHere(), /failed/);
});

test('await in finally 会延迟外层完成，并可覆盖原失败', async () => {
  const events = [];

  async function cleanup() {
    try {
      throw new Error('operation failed');
    } finally {
      await Promise.resolve();
      events.push('cleanup completed');
    }
  }

  await assert.rejects(cleanup(), /operation failed/);
  assert.deepEqual(events, ['cleanup completed']);

  async function brokenCleanup() {
    try {
      throw new Error('operation failed');
    } finally {
      throw new Error('cleanup failed');
    }
  }
  await assert.rejects(brokenCleanup(), /cleanup failed/);
});

test('async 方法和 async 箭头保留各自的 this 规则', async () => {
  const owner = {
    value: 7,
    async method() {
      await Promise.resolve();
      return this.value;
    },
    createArrow() {
      return async () => {
        await Promise.resolve();
        return this.value;
      };
    },
  };

  assert.equal(await owner.method(), 7);
  const detachedMethod = owner.method;
  await assert.rejects(detachedMethod(), TypeError);

  const arrow = owner.createArrow();
  assert.equal(await arrow.call({ value: 9 }), 7);
});
