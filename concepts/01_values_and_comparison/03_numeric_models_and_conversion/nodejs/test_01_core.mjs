// 数值模型与转换。
// 共同问题：整数是否溢出；浮点特殊值如何表现；显式转换如何报告失败；
// 混合运算采用什么结果类型。
//
// polyglot-family: values_and_comparison
// polyglot-concept: numeric_models_and_conversion
// polyglot-related: languages/nodejs/language/test_001_primitive_values_numeric_models_and_equality.mjs
// polyglot-related: languages/nodejs/language/test_021_number_math_bigint_formatting_and_integer_operations.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Number 是双精度浮点，BigInt 才保存任意精度整数', () => {
  assert.equal(Number.MAX_SAFE_INTEGER + 1, Number.MAX_SAFE_INTEGER + 2);
  assert.equal(2n ** 100n + 1n, 1267650600228229401496703205377n);
  assert.equal(typeof 1, 'number');
  assert.equal(typeof 1n, 'bigint');
});

test('Number 保留 NaN、无穷与负零', () => {
  assert.equal(Number.isNaN(Number.NaN), true);
  assert.equal(Number.POSITIVE_INFINITY > Number.MAX_VALUE, true);
  assert.equal(Object.is(-0, 0), false);
  assert.equal(1 / -0, Number.NEGATIVE_INFINITY);
});

test('显式转换的严格程度不同，失败信号也不同', () => {
  assert.equal(Number('12.5'), 12.5);
  assert.equal(Number('12px'), Number.NaN);
  assert.equal(Number.parseInt('12px', 10), 12);
  assert.equal(BigInt('9007199254740993'), 9007199254740993n);
  assert.throws(() => BigInt('1.5'), SyntaxError);
});

test('Number 与 BigInt 不能隐式混合算术', () => {
  assert.throws(() => 1n + 1, TypeError);
  assert.equal(Number(1n) + 1, 2);
  assert.equal(BigInt(1) + 1n, 2n);

  // JavaScript 不会像 Python 一样把这两种整数模型自动提升到共同类型。
});
