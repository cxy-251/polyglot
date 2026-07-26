// 序列修改与失效。
// 共同问题：修改容器后迭代器和视图是否仍有效；遍历期间修改会发生什么；
// 哪些结构能检测不安全的结构变化。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/nodejs/language/test_011_arrays_holes_mutation_copying_sorting_and_species.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('数组 iterator 会观察在游标之后追加的元素', () => {
  const values = [1, 2];
  const iterator = values.values();

  assert.equal(iterator.next().value, 1);
  values.push(3);
  assert.deepEqual([...iterator], [2, 3]);
});

test('Map iterator 也会访问迭代期间新增且尚未访问的键', () => {
  const mapping = new Map([['a', 1]]);
  const iterator = mapping.keys();

  assert.equal(iterator.next().value, 'a');
  mapping.set('b', 2);
  assert.deepEqual([...iterator], ['b']);
});

test('TypedArray 视图共享固定长度存储', () => {
  const storage = new ArrayBuffer(3);
  const first = new Uint8Array(storage);
  const second = new Uint8Array(storage);

  first[0] = 9;

  assert.equal(second[0], 9);
  assert.equal(first.length, 3);
});

test('复制后遍历可避免修改原数组影响游标', () => {
  const values = [1, 2, 3];

  for (const value of [...values]) {
    if (value % 2 === 1) {
      values.splice(values.indexOf(value), 1);
    }
  }

  assert.deepEqual(values, [2]);
});

