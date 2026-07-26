// Unicode 字符串、编码单元与用户可见字符。
// 共同问题：长度和索引按什么单位；编码何时变成字节；组合字符是否等于一个元素；
// 非法编码如何报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/nodejs/language/test_013_strings_unicode_templates_and_text_operations.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('字符串长度和索引按 UTF-16 code unit', () => {
  const text = 'A😀';

  assert.equal(text.length, 3);
  assert.equal(text[1].length, 1);
  assert.equal(text.codePointAt(1), 0x1f600);
});

test('字符串迭代按 code point 前进', () => {
  assert.deepEqual([...'A😀'], ['A', '😀']);
});

test('TextEncoder 把字符串编码为 UTF-8 字节', () => {
  const encoded = new TextEncoder().encode('咖啡');

  assert.equal(encoded.byteLength, 6);
  assert.equal(new TextDecoder().decode(encoded), '咖啡');
});

test('grapheme cluster 仍可能包含多个 code point', () => {
  const text = 'e\u0301';
  const segments = [...new Intl.Segmenter('en', { granularity: 'grapheme' }).segment(text)];

  assert.equal(text.length, 2);
  assert.equal([...text].length, 2);
  assert.equal(segments.length, 1);
});

