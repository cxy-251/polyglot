// 提前终止的关闭协议与委托。
// 共同问题：消费方提前停止时是否通知生产方；清理如何穿过委托层；
// 关闭失败如何传播给消费方。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/nodejs/language/test_016_iterables_iterators_generators_and_iterator_closing.mjs
// polyglot-related: languages/nodejs/language/test_026_iterator_helpers_laziness_composition_and_closing.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('iterator helper take 到达上限时关闭底层生成器', () => {
  const events = [];

  function* values() {
    try {
      yield 1;
      yield 2;
    } finally {
      events.push('closed');
    }
  }

  const collected = Iterator.from(values()).take(1).toArray();

  assert.deepEqual(collected, [1]);
  assert.deepEqual(events, ['closed']);
});

test('IteratorClose 的 return 失败会传播给消费方', () => {
  const closeError = new Error('close failed');
  const iterable = {
    [Symbol.iterator]() {
      return {
        next: () => ({ value: 1, done: false }),
        return: () => {
          throw closeError;
        },
      };
    },
  };

  assert.throws(() => {
    for (const _ of iterable) {
      break;
    }
  }, (error) => error === closeError);

  // for-of 的 break 执行 IteratorClose；这比 C++ range-for 多一个标准关闭入口。
});
