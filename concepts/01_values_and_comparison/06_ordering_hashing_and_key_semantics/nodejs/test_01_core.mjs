// 排序、哈希与键语义。
// 共同问题：排序依赖什么关系；相等对象是否必须同哈希；哪些值能作为键；
// 映射与集合如何判断同一个键。
//
// polyglot-family: values_and_comparison
// polyglot-concept: ordering_hashing_and_key_semantics
// polyglot-related: languages/nodejs/language/test_011_arrays_holes_mutation_copying_sorting_and_species.mjs
// polyglot-related: languages/nodejs/language/test_015_map_set_weak_collections_and_set_composition.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Map 和 Set 使用 SameValueZero 判断原始值键', () => {
  const mapping = new Map([
    [Number.NaN, 'first'],
    [Number.NaN, 'replacement'],
    [-0, 'zero'],
  ]);
  const values = new Set([0, -0, Number.NaN, Number.NaN]);

  assert.equal(mapping.size, 2);
  assert.equal(mapping.get(Number.NaN), 'replacement');
  assert.equal(mapping.get(0), 'zero');
  assert.equal(values.size, 2);
});

test('对象键按身份区分，不能提供 Python 或 C++ 式用户哈希', () => {
  const first = { number: 2 };
  const sameValue = { number: 2 };
  const mapping = new Map([
    [first, 'first'],
    [sameValue, 'second'],
  ]);

  assert.equal(mapping.size, 2);
  assert.equal(mapping.get(first), 'first');

  // valueOf、Symbol.toPrimitive 不参与 Map 键匹配；语言没有用户可见的 hash 协议。
});

test('数组排序需要比较器才能获得数值顺序', () => {
  const values = [10, 2, 1];

  assert.deepEqual(values.toSorted(), [1, 10, 2]);
  assert.deepEqual(values.toSorted((left, right) => left - right), [1, 2, 10]);
});

test('现代数组排序稳定保留同键元素的输入顺序', () => {
  const records = [
    { group: 1, id: 'a' },
    { group: 0, id: 'b' },
    { group: 1, id: 'c' },
  ];

  const sorted = records.toSorted((left, right) => left.group - right.group);
  assert.deepEqual(sorted.map(({ id }) => id), ['b', 'a', 'c']);
});
