// 索引、切片与边界。
// 共同问题：负索引如何解释；切片是否复制；越界如何报告；
// 自定义类型通过什么入口接收索引与切片。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: indexing_slicing_and_bounds
// polyglot-related: languages/nodejs/language/test_011_arrays_holes_mutation_copying_sorting_and_species.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('方括号中的负数是普通属性键，at 才从末尾计数', () => {
  const values = ['a', 'b', 'c'];

  assert.equal(values[-1], undefined);
  assert.equal(values.at(-1), 'c');
  assert.equal(values.at(-3), 'a');
});

test('slice 规范化边界并返回浅复制数组', () => {
  const nested = { value: 1 };
  const values = [0, nested, 2, 3];
  const sliced = values.slice(-3, 10);

  assert.deepEqual(sliced, [nested, 2, 3]);
  assert.notEqual(sliced, values);
  assert.equal(sliced[0], nested);
});

test('数组越界读取返回 undefined 而不是抛错', () => {
  const values = [1, 2];

  assert.equal(values[2], undefined);
  assert.deepEqual(values.slice(2, 100), []);
});

test('Proxy 可以观察属性键但语言没有 slice 协议对象', () => {
  const keys = [];
  const value = new Proxy([1, 2], {
    get(target, key, receiver) {
      keys.push(key);
      return Reflect.get(target, key, receiver);
    },
  });

  assert.equal(value[0], 1);
  assert.equal(keys[0], '0');
});

