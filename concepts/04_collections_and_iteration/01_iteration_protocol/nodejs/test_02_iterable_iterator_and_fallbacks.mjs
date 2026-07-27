// 可迭代对象、迭代器与协议 fallback。
// 共同问题：容器与单次游标如何区分；每次取得迭代器是否共享状态；
// 缺少主要协议入口时是否存在兼容 fallback。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/nodejs/language/test_016_iterables_iterators_generators_and_iterator_closing.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('iterator 可迭代为自身，数组每次产生独立 iterator', () => {
  const values = [1, 2];
  const first = values[Symbol.iterator]();
  const second = values[Symbol.iterator]();

  assert.equal(first[Symbol.iterator](), first);
  assert.notEqual(first, second);
  assert.equal(first.next().value, 1);
  assert.equal(second.next().value, 1);
});

test('数值属性本身不会让普通对象成为 iterable', () => {
  const arrayLike = { 0: 'a', 1: 'b', length: 2 };

  assert.throws(() => [...arrayLike], TypeError);

  arrayLike[Symbol.iterator] = Array.prototype[Symbol.iterator];
  assert.deepEqual([...arrayLike], ['a', 'b']);

  // JavaScript 必须显式提供 Symbol.iterator；它不像 Python 那样从连续 __getitem__
  // 调用建立兼容迭代，也不像 C++ 通过 begin/end CPO 查找 range。
});
