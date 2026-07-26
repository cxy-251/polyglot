// 空值、缺失状态与可选值。
// 共同问题：语言有几种空状态；缺失成员如何区分；默认值是否会吞掉有效假值；
// 读取空状态时在何处失败。
//
// polyglot-family: values_and_comparison
// polyglot-concept: null_missing_and_optional_values
// polyglot-related: languages/nodejs/language/test_001_primitive_values_numeric_models_and_equality.mjs
// polyglot-related: languages/nodejs/language/test_003_expressions_operators_evaluation_and_short_circuiting.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('null 与 undefined 是不同空值，未声明绑定会直接失败', () => {
  assert.equal(null === undefined, false);
  assert.equal(typeof undefined, 'undefined');
  assert.equal(typeof null, 'object');
  assert.throws(() => missingBinding, ReferenceError);
});

test('属性存在性区分缺失与值为 undefined', () => {
  const settings = { timeout: undefined };

  assert.equal(settings.timeout, undefined);
  assert.equal(settings.missing, undefined);
  assert.equal(Object.hasOwn(settings, 'timeout'), true);
  assert.equal(Object.hasOwn(settings, 'missing'), false);
});

test('空值合并只替换 nullish，逻辑或会替换所有假值', () => {
  assert.equal(0 ?? 10, 0);
  assert.equal('' ?? 'fallback', '');
  assert.equal(null ?? 'fallback', 'fallback');
  assert.equal(0 || 10, 10);
});

test('可选链短路 nullish 接收者但不会隐藏 getter 异常', () => {
  assert.equal(null?.profile?.name, undefined);

  const value = {
    get profile() {
      throw new Error('getter failed');
    },
  };
  assert.throws(() => value?.profile?.name, /getter failed/);
});

