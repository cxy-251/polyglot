// polyglot-covers:
// - nodejs.language.async-iterator-protocol
// - nodejs.language.for-await-of
// - nodejs.language.async-generator-state
// - nodejs.language.async-generator-yield-and-return
// - nodejs.language.async-yield-star
// - nodejs.language.async-iterator-closing
// - nodejs.language.sync-iterable-fallback-in-for-await

import assert from 'node:assert/strict';
import test from 'node:test';

test('异步 iterator 的 next 返回 Promise 包装的结果记录', async () => {
  const asyncRange = {
    [Symbol.asyncIterator]() {
      let current = 1;
      return {
        async next() {
          return current <= 3
            ? { done: false, value: current++ }
            : { done: true, value: undefined };
        },
      };
    },
  };

  const iterator = asyncRange[Symbol.asyncIterator]();
  const pending = iterator.next();
  assert.equal(pending instanceof Promise, true);
  assert.deepEqual(await pending, { done: false, value: 1 });

  const values = [];
  for await (const value of asyncRange) {
    values.push(value);
  }
  assert.deepEqual(values, [1, 2, 3]);
});

test('for-await 也能消费同步 iterable，并 await 每个值', async () => {
  const values = [Promise.resolve(1), 2, Promise.resolve(3)];
  const received = [];

  for await (const value of values) {
    received.push(value);
  }

  assert.deepEqual(received, [1, 2, 3]);

  // 即使输入全是同步值，for-await 每轮仍经过 Promise 解包，热路径不应无意替代 for-of。
});

test('对象同时提供两种协议时，for-await 优先异步协议', async () => {
  const source = {
    *[Symbol.iterator]() {
      yield 'sync';
    },
    async *[Symbol.asyncIterator]() {
      yield 'async';
    },
  };

  assert.deepEqual([...source], ['sync']);

  const values = [];
  for await (const value of source) {
    values.push(value);
  }
  assert.deepEqual(values, ['async']);
});

test('异步生成器同时实现异步 iterable 与 iterator', async () => {
  async function* sequence() {
    yield 1;
    yield Promise.resolve(2);
    return 3;
  }

  const generator = sequence();
  assert.equal(generator[Symbol.asyncIterator](), generator);
  assert.deepEqual(await generator.next(), { done: false, value: 1 });
  assert.deepEqual(await generator.next(), { done: false, value: 2 });
  assert.deepEqual(await generator.next(), { done: true, value: 3 });
});

test('异步生成器可 await 输入再 yield 输出', async () => {
  async function* transform(values) {
    for await (const value of values) {
      yield value * 2;
    }
  }

  const received = [];
  for await (const value of transform([1, Promise.resolve(2), 3])) {
    received.push(value);
  }
  assert.deepEqual(received, [2, 4, 6]);
});

test('异步生成器的 next 参数送回上一个 yield', async () => {
  async function* conversation() {
    const answer = yield 'question';
    return `answer:${answer}`;
  }

  const generator = conversation();
  assert.deepEqual(await generator.next(), {
    done: false,
    value: 'question',
  });
  assert.deepEqual(await generator.next('ready'), {
    done: true,
    value: 'answer:ready',
  });
});

test('提前退出 for-await 会 await iterator.return 完成清理', async () => {
  const events = [];
  const source = {
    [Symbol.asyncIterator]() {
      return {
        async next() {
          events.push('next');
          return { done: false, value: 1 };
        },
        async return() {
          await Promise.resolve();
          events.push('return completed');
          return { done: true };
        },
      };
    },
  };

  for await (const value of source) {
    assert.equal(value, 1);
    break;
  }
  assert.deepEqual(events, ['next', 'return completed']);
});

test('异步生成器 finally 在 return 和循环提前退出时执行', async () => {
  const events = [];

  async function* resource() {
    try {
      events.push('open');
      yield 1;
      yield 2;
    } finally {
      events.push('close');
    }
  }

  for await (const value of resource()) {
    assert.equal(value, 1);
    break;
  }
  assert.deepEqual(events, ['open', 'close']);
});

test('yield* 可委托同步或异步 iterable', async () => {
  async function* asyncInner() {
    yield 3;
    return 'async result';
  }

  async function* combined() {
    yield* [1, Promise.resolve(2)];
    const result = yield* asyncInner();
    yield result;
  }

  const values = [];
  for await (const value of combined()) {
    values.push(value);
  }
  assert.deepEqual(values, [1, 2, 3, 'async result']);
});
