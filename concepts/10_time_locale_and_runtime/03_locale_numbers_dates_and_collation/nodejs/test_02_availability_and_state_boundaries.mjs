// 区域可用性和状态边界。
// 共同问题：区域数据缺失时如何失败；排序是否等于代码点顺序；
// 区域配置属于显式对象还是可泄漏到其他代码的进程状态。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/nodejs/language/
// polyglot-related+: test_023_intl_number_date_relative_and_plural_formatting.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('supportedLocalesOf 报告当前 ICU 真正支持的请求', () => {
  const requested = ['de-DE', 'en-US'];
  const supported = Intl.NumberFormat.supportedLocalesOf(requested);

  assert.deepEqual(supported, requested);
  assert.throws(() => new Intl.NumberFormat('not_a_locale'), RangeError);
});

test('显式格式器保持独立配置而不修改进程默认区域', () => {
  const us = new Intl.NumberFormat('en-US');
  const german = new Intl.NumberFormat('de-DE');

  assert.equal(us.resolvedOptions().locale, 'en-US');
  assert.equal(german.resolvedOptions().locale, 'de-DE');
  assert.equal(us.format(1234.5), '1,234.5');
  assert.equal(german.format(1234.5), '1.234,5');
});

test('自然语言 collation 可以不同于 UTF-16 code unit 顺序', () => {
  const values = ['ä', 'z'];
  const codeUnitOrder = [...values].sort();
  const germanOrder = [...values].sort(new Intl.Collator('de').compare);

  assert.deepEqual(codeUnitOrder, ['z', 'ä']);
  assert.deepEqual(germanOrder, ['ä', 'z']);
});
