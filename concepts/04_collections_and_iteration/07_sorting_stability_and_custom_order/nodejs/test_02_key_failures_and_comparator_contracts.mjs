// 排序回调、失败与次序契约。
// 共同问题：排序回调可能调用多少次；回调失败时输入是否改变；
// 不一致的次序关系是否由运行时修复。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/nodejs/language/test_011_arrays_holes_mutation_copying_sorting_and_species.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('toSorted 比较器失败时不修改原数组', () => {
  const failure = new Error('cannot rank');
  const values = [3, 1, 2];

  assert.throws(
    () => values.toSorted(() => {
      throw failure;
    }),
    (error) => error === failure,
  );

  assert.deepEqual(values, [3, 1, 2]);
});

test('NaN 比较结果按相等处理且稳定保留输入顺序', () => {
  const values = [
    { id: 'a', group: 1 },
    { id: 'b', group: 1 },
  ];
  let calls = 0;

  const sorted = values.toSorted(() => {
    calls += 1;
    return Number.NaN;
  });

  assert.deepEqual(sorted.map(({ id }) => id), ['a', 'b']);
  assert.ok(calls > 0);

  // comparator 可重复调用；调用次数不属于接口。非传递或非反对称比较器不满足约定，
  // 结果可能因引擎与输入改变，不能通过单次输出把偶然行为写成规则。
});
