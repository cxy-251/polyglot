// 视图、复制与结构修改边界。
// 共同问题：派生对象是独立副本还是共享视图；哪些修改保持现有游标有效；
// 安全删除循环应基于什么稳定观察。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/nodejs/language/test_011_arrays_holes_mutation_copying_sorting_and_species.mjs
// polyglot-related: languages/nodejs/language/test_012_arraybuffer_typedarray_dataview_and_binary_memory.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Array slice 是浅复制，TypedArray subarray 是共享视图', () => {
  const values = [1, 2, 3];
  const copied = values.slice(1);
  const storage = new Uint8Array([1, 2, 3]);
  const view = storage.subarray(1);

  copied[0] = 9;
  view[0] = 8;

  assert.deepEqual(values, [1, 2, 3]);
  assert.deepEqual(copied, [9, 3]);
  assert.deepEqual([...storage], [1, 8, 3]);
});

test('数组 iterator 按当前 length 推进，删除尾部可缩短剩余序列', () => {
  const values = [1, 2, 3];
  const iterator = values.values();

  assert.equal(iterator.next().value, 1);
  values.length = 1;

  assert.deepEqual(iterator.next(), { value: undefined, done: true });

  // ECMAScript 数组 iterator 不抛“结构已修改”；它每次推进读取当前 length。与 C++
  // iterator 失效、Python dict size 检测都不是同一机制。
});

test('先收集索引再逆序删除避免位置移动影响待处理项', () => {
  const values = [1, 2, 3, 4];
  const indexes = values
    .map((value, index) => ({ value, index }))
    .filter(({ value }) => value % 2 === 1)
    .map(({ index }) => index)
    .reverse();

  for (const index of indexes) {
    values.splice(index, 1);
  }

  assert.deepEqual(values, [2, 4]);
});
