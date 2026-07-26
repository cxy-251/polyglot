// 同步迭代协议。
// 共同问题：如何取得迭代器；推进与完成如何表示；迭代器能否复用；
// 提前退出是否自动触发关闭协议。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/nodejs/language/test_016_iterables_iterators_generators_and_iterator_closing.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Symbol.iterator 取得 iterator，next 返回 value/done 记录', () => {
  const iterator = [1, 2][Symbol.iterator]();

  assert.deepEqual(iterator.next(), { value: 1, done: false });
  assert.deepEqual(iterator.next(), { value: 2, done: false });
  assert.deepEqual(iterator.next(), { value: undefined, done: true });
});

test('数组可重复迭代，iterator 是单次游标', () => {
  const values = [1, 2];
  const iterator = values[Symbol.iterator]();

  assert.deepEqual([...values], [1, 2]);
  assert.deepEqual([...values], [1, 2]);
  assert.deepEqual([...iterator], [1, 2]);
  assert.deepEqual([...iterator], []);
});

test('自定义 iterable 可以为每次迭代创建独立状态', () => {
  const range = {
    *[Symbol.iterator]() {
      yield 1;
      yield 2;
    },
  };

  assert.deepEqual([...range], [1, 2]);
  assert.deepEqual([...range], [1, 2]);
});

test('for-of 提前退出会调用 iterator.return', () => {
  const events = [];
  function* values() {
    try {
      yield 1;
      yield 2;
    } finally {
      events.push('closed');
    }
  }

  for (const _ of values()) {
    break;
  }

  assert.deepEqual(events, ['closed']);
});
