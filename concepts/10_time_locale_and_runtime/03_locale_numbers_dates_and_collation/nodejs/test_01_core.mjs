// 区域化数字、日期与排序。
// 共同问题：数字和日期如何按区域呈现；文本排序是否等于码点顺序；
// 区域设置是显式对象还是进程全局状态；缺少区域数据时如何处理。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/nodejs/language/
// polyglot-related+: test_023_intl_number_date_relative_and_plural_formatting.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('NumberFormat 将区域作为独立格式器配置', () => {
  const us = new Intl.NumberFormat('en-US').format(1234.5);
  const germany = new Intl.NumberFormat('de-DE').format(1234.5);

  assert.equal(us, '1,234.5');
  assert.equal(germany, '1.234,5');
});

test('DateTimeFormat 同时固定区域和时区', () => {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    dateStyle: 'medium',
    timeZone: 'UTC',
  });

  assert.equal(formatter.format(new Date('2024-01-01T00:00:00Z')), 'Jan 1, 2024');
});

test('Collator 可以采用数字感知排序', () => {
  const collator = new Intl.Collator('en', { numeric: true });

  assert.deepEqual(['file10', 'file2'].sort(collator.compare), ['file2', 'file10']);
});

test('Segmenter 按书写系统规则而不是 UTF-16 单元分词素', () => {
  const segments = [...new Intl.Segmenter('en', { granularity: 'grapheme' }).segment('e\u0301')];

  assert.equal(segments.length, 1);
  assert.equal(segments[0].segment, 'e\u0301');
});
