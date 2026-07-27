// 规范化、非法编码与无损边界。
// 共同问题：规范等价文本是否自动相等；非法输入是拒绝、替换还是保留；
// 字符串模型能否直接表达孤立编码单元。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/nodejs/language/test_013_strings_unicode_templates_and_text_operations.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('字符串规范化必须显式请求', () => {
  const composed = '\u00e9';
  const decomposed = 'e\u0301';

  assert.notEqual(composed, decomposed);
  assert.equal(decomposed.normalize('NFC'), composed);
  assert.equal(composed.normalize('NFD'), decomposed);
});

test('TextDecoder 可选择 replacement 或 fatal 策略', () => {
  const invalid = Uint8Array.of(0x61, 0xff, 0x62);

  assert.equal(new TextDecoder().decode(invalid), 'a\ufffdb');
  assert.throws(
    () => new TextDecoder('utf-8', { fatal: true }).decode(invalid),
    TypeError,
  );
});

test('TextEncoder 把孤立 surrogate 替换为 U+FFFD', () => {
  const loneSurrogate = '\ud800';
  const encoded = new TextEncoder().encode(loneSurrogate);

  assert.deepEqual([...encoded], [0xef, 0xbf, 0xbd]);
  assert.equal(new TextDecoder().decode(encoded), '\ufffd');

  // ECMAScript String 可保存孤立 UTF-16 code unit；标准 TextEncoder 采用 well-formed
  // 转换并丢失原单元。若必须无损保存，应使用显式 Uint16Array/二进制协议。
});
