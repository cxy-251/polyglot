// 横向概念 002｜值相等、对象身份与数值特例。
// 共同问题：跨数值类型是否转换；NaN 和负零如何比较；集合按内容还是身份比较；
// 自定义对象能否提供值语义。
//
// polyglot-concept: equality
// polyglot-related: languages/nodejs/language/test_001_primitive_values_numeric_models_and_equality.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('严格、宽松与 SameValue 相等回答不同问题', () => {
  assert.equal(1 === 1.0, true);
  assert.equal(1 === '1', false);
  assert.equal(1 == '1', true);

  assert.equal(Number.NaN === Number.NaN, false);
  assert.equal(Object.is(Number.NaN, Number.NaN), true);
  assert.equal(0 === -0, true);
  assert.equal(Object.is(0, -0), false);
});

test('数组和普通对象只按身份参与语言相等运算', () => {
  const first = [1, 2];
  const sameValue = [1, 2];
  const alias = first;

  assert.equal(first === sameValue, false);
  assert.equal(first === alias, true);

  // assert.deepEqual 能比较结构，但它是测试库算法，不是 JavaScript 的 === 语义。
  assert.deepEqual(first, sameValue);
});

test('对象转换钩子只影响宽松相等，不能重载严格相等', () => {
  let conversionCalls = 0;
  const version = {
    valueOf() {
      conversionCalls += 1;
      return 24;
    },
  };

  assert.equal(version === 24, false);
  assert.equal(conversionCalls, 0);
  assert.equal(version == 24, true);
  assert.equal(conversionCalls, 1);
});
