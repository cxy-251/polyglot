// 格式化、解析与插值。
// 共同问题：插值何时求值；格式说明如何控制表示；解析是否接受前缀；
// 失败通过异常还是特殊值报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: formatting_parsing_and_interpolation
// polyglot-related: languages/nodejs/language/test_013_strings_unicode_templates_and_text_operations.mjs
// polyglot-related: languages/nodejs/language/test_021_number_math_bigint_formatting_and_integer_operations.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('模板字面量按顺序求值并执行字符串转换', () => {
  const events = [];
  const value = {
    toString() {
      events.push('convert');
      return 'value';
    },
  };

  assert.equal(`result:${value}`, 'result:value');
  assert.deepEqual(events, ['convert']);
});

test('tagged template 分离固定文本与未拼接值', () => {
  const tag = (strings, ...values) => ({ strings, values });
  const result = tag`count:${2}`;

  assert.deepEqual([...result.strings], ['count:', '']);
  assert.deepEqual(result.values, [2]);
});

test('Number 要求完整数值，parseInt 接受有效前缀', () => {
  assert.equal(Number('12px'), Number.NaN);
  assert.equal(Number.parseInt('12px', 10), 12);
  assert.equal(Number.parseInt('101', 2), 5);
});

test('数字格式方法显式选择精度与进制', () => {
  assert.equal((12.345).toFixed(2), '12.35');
  assert.equal((255).toString(16), 'ff');
});
