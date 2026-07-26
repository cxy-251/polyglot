// 集合成员、去重与运算。
// 共同问题：集合使用哪种相等关系；是否保持顺序；如何表达集合运算；
// 可变集合能否作为另一个集合的成员。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sets_membership_and_deduplication
// polyglot-related: languages/nodejs/language/test_015_map_set_weak_collections_and_set_composition.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Set 使用 SameValueZero 并保持首次插入顺序', () => {
  const values = new Set([2, 1, 2, Number.NaN, Number.NaN, -0, 0]);

  assert.deepEqual([...values], [2, 1, Number.NaN, 0]);
  assert.equal(values.has(Number.NaN), true);
});

test('对象按身份去重而不是按内容', () => {
  const first = { value: 1 };
  const sameValue = { value: 1 };
  const values = new Set([first, sameValue, first]);

  assert.equal(values.size, 2);
  assert.equal(values.has(first), true);
});

test('标准集合组合方法返回新集合', () => {
  const left = new Set([1, 2]);
  const right = new Set([2, 3]);

  assert.deepEqual([...left.union(right)], [1, 2, 3]);
  assert.deepEqual([...left.intersection(right)], [2]);
  assert.deepEqual([...left.difference(right)], [1]);
  assert.deepEqual([...left.symmetricDifference(right)], [1, 3]);
});

test('可变对象可以成为成员，后续修改不改变其身份键', () => {
  const value = { state: 1 };
  const values = new Set([value]);

  value.state = 2;

  assert.equal(values.has(value), true);
  // Python set/C++ unordered_set 的值变更可能破坏哈希契约；JS 对象键始终按身份。
});
