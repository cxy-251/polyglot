// polyglot-covers:
// - nodejs.language.intl-number-format
// - nodejs.language.intl-currency-unit-and-compact-notation
// - nodejs.language.intl-format-to-parts
// - nodejs.language.intl-date-time-format
// - nodejs.language.intl-format-range
// - nodejs.language.intl-relative-time-format
// - nodejs.language.intl-plural-rules

import assert from 'node:assert/strict';
import test from 'node:test';

test('NumberFormat 按 locale 处理分组、小数和数字符号', () => {
  const us = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
  const german = new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });

  assert.equal(us.format(1234567.8), '1,234,567.80');
  assert.equal(german.format(1234567.8), '1.234.567,80');
  assert.equal(us.resolvedOptions().locale, 'en-US');
  assert.equal(us.resolvedOptions().numberingSystem, 'latn');
});

test('currency、unit 和 compact notation 表达不同领域格式', () => {
  const currency = new Intl.NumberFormat('en-US', {
    currency: 'USD',
    style: 'currency',
  });
  const unit = new Intl.NumberFormat('en-US', {
    style: 'unit',
    unit: 'kilometer-per-hour',
    unitDisplay: 'long',
  });
  const compact = new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  });

  assert.equal(currency.format(1234.5), '$1,234.50');
  assert.equal(unit.format(80), '80 kilometers per hour');
  assert.equal(compact.format(1_250_000), '1.3M');

  // 货币格式只展示，不执行汇率换算；调用方必须先提供正确币种的数值。
});

test('formatToParts 适合安全重排或样式化，而不是拆格式化字符串', () => {
  const formatter = new Intl.NumberFormat('en-US', {
    currency: 'USD',
    style: 'currency',
  });
  const parts = formatter.formatToParts(1234.5);

  assert.deepEqual(parts.map(({ type }) => type), [
    'currency',
    'integer',
    'group',
    'integer',
    'decimal',
    'fraction',
  ]);
  assert.equal(parts.map(({ value }) => value).join(''), '$1,234.50');
});

test('DateTimeFormat 通过 timeZone 得到与主机本地时区无关的结果', () => {
  const instant = new Date('2026-07-22T12:34:56.000Z');
  const formatter = new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'full',
    timeStyle: 'long',
    timeZone: 'UTC',
  });

  assert.equal(
    formatter.format(instant),
    'Wednesday, 22 July 2026 at 12:34:56 UTC',
  );
  assert.equal(formatter.resolvedOptions().timeZone, 'UTC');
});

test('DateTimeFormat parts 暴露语义字段而不是固定标点位置', () => {
  const formatter = new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    month: 'short',
    timeZone: 'UTC',
    year: 'numeric',
  });
  const parts = formatter.formatToParts(new Date('2026-07-22T00:00:00Z'));
  const fields = Object.fromEntries(
    parts
      .filter(({ type }) => type !== 'literal')
      .map(({ type, value }) => [type, value]),
  );

  assert.deepEqual(fields, {
    day: '22',
    month: 'Jul',
    year: '2026',
  });
});

test('formatRange 合并共同字段，formatRangeToParts 标记来源', () => {
  const formatter = new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
    year: 'numeric',
  });
  const start = new Date('2026-07-22T00:00:00Z');
  const end = new Date('2026-07-24T00:00:00Z');

  assert.equal(formatter.formatRange(start, end), 'Jul 22 – 24, 2026');
  const sources = new Set(
    formatter.formatRangeToParts(start, end).map(({ source }) => source),
  );
  assert.deepEqual(sources, new Set(['shared', 'startRange', 'endRange']));
});

test('RelativeTimeFormat 的 numeric auto 可选择 yesterday 等词语', () => {
  const always = new Intl.RelativeTimeFormat('en-US', {
    numeric: 'always',
  });
  const automatic = new Intl.RelativeTimeFormat('en-US', {
    numeric: 'auto',
  });

  assert.equal(always.format(-1, 'day'), '1 day ago');
  assert.equal(always.format(2, 'day'), 'in 2 days');
  assert.equal(automatic.format(-1, 'day'), 'yesterday');
  assert.equal(automatic.format(0, 'day'), 'today');
});

test('PluralRules 返回语言相关类别，不等同于 value === 1', () => {
  const english = new Intl.PluralRules('en-US');
  const arabic = new Intl.PluralRules('ar');

  assert.equal(english.select(1), 'one');
  assert.equal(english.select(2), 'other');
  assert.equal(english.select(1.5), 'other');
  assert.equal(arabic.select(0), 'zero');
  assert.equal(arabic.select(2), 'two');
  assert.ok(arabic.resolvedOptions().pluralCategories.includes('few'));
});

test('ordinal PluralRules 与 cardinal 使用不同类别规则', () => {
  const ordinal = new Intl.PluralRules('en-US', { type: 'ordinal' });

  assert.deepEqual([1, 2, 3, 4, 11, 21].map((value) => ordinal.select(value)), [
    'one',
    'two',
    'few',
    'other',
    'other',
    'one',
  ]);
});
