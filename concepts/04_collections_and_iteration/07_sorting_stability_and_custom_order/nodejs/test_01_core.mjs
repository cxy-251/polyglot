// 排序稳定性与自定义次序。
// 共同问题：默认顺序是什么；排序是否稳定；key/comparator 调用模型如何；
// 排序是原地操作还是返回副本。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/nodejs/language/test_011_arrays_holes_mutation_copying_sorting_and_species.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('sort 原地修改，toSorted 返回副本', () => {
  const original = [3, 1, 2];
  const copied = original.toSorted((left, right) => left - right);

  assert.deepEqual(copied, [1, 2, 3]);
  assert.deepEqual(original, [3, 1, 2]);
  assert.equal(original.sort(), original);
});

test('默认排序把元素转换成字符串', () => {
  assert.deepEqual([10, 2, 1].toSorted(), [1, 10, 2]);
  assert.deepEqual([10, 2, 1].toSorted((left, right) => left - right), [1, 2, 10]);
});

test('数组排序稳定保留相同键的输入顺序', () => {
  const records = [
    { id: 'a', group: 1 },
    { id: 'b', group: 0 },
    { id: 'c', group: 1 },
  ];

  const sorted = records.toSorted((left, right) => left.group - right.group);
  assert.deepEqual(sorted.map(({ id }) => id), ['b', 'a', 'c']);
});

test('比较器通过负数、零、正数表达顺序', () => {
  const descending = [1, 3, 2].toSorted((left, right) => right - left);

  assert.deepEqual(descending, [3, 2, 1]);

  // Python key 通常每项只调用一次；JavaScript comparator 可对同一元素调用多次。
});
