// polyglot-covers:
// - nodejs.language.intl-locale-and-canonicalization
// - nodejs.language.intl-collator
// - nodejs.language.intl-segmenter
// - nodejs.language.intl-list-format
// - nodejs.language.intl-display-names
// - nodejs.language.intl-supported-values

import assert from 'node:assert/strict';
import test from 'node:test';

test('getCanonicalLocales 规范化标签并去重', () => {
  assert.deepEqual(Intl.getCanonicalLocales(['EN-us', 'en-US', 'zh-hans-cn']), [
    'en-US',
    'zh-Hans-CN',
  ]);
  assert.throws(() => Intl.getCanonicalLocales('not_a_locale'), RangeError);
});

test('Intl.Locale 暴露标签字段、Unicode 扩展和最大化信息', () => {
  const locale = new Intl.Locale('zh-CN-u-ca-chinese-nu-hanidec');

  assert.equal(locale.language, 'zh');
  assert.equal(locale.region, 'CN');
  assert.equal(locale.calendar, 'chinese');
  assert.equal(locale.numberingSystem, 'hanidec');
  assert.equal(locale.baseName, 'zh-CN');

  const maximized = new Intl.Locale('zh').maximize();
  assert.equal(maximized.toString(), 'zh-Hans-CN');
  assert.equal(maximized.minimize().toString(), 'zh');
});

test('Collator.compare 提供语言排序，不能依赖返回值恰好为 -1 或 1', () => {
  const collator = new Intl.Collator('de-DE');
  assert.ok(collator.compare('ä', 'z') < 0);

  const values = ['z', 'ä', 'a'];
  assert.deepEqual(values.toSorted(collator.compare), ['a', 'ä', 'z']);

  // 规范只保证负数、零、正数的符号；实现可以返回任何幅度。
  assert.equal(Math.sign(collator.compare('a', 'a')), 0);
});

test('Collator numeric 与 sensitivity 适用于自然编号和搜索', () => {
  const lexical = new Intl.Collator('en-US');
  const numeric = new Intl.Collator('en-US', { numeric: true });

  assert.deepEqual(['file10', 'file2'].toSorted(lexical.compare), ['file10', 'file2']);
  assert.deepEqual(['file10', 'file2'].toSorted(numeric.compare), ['file2', 'file10']);

  const base = new Intl.Collator('en-US', {
    sensitivity: 'base',
    usage: 'search',
  });
  assert.equal(base.compare('resume', 'résumé'), 0);
  assert.notEqual(new Intl.Collator('en-US').compare('resume', 'résumé'), 0);
});

test('Segmenter 按 grapheme cluster 切分用户可见字符', () => {
  const segmenter = new Intl.Segmenter('en-US', {
    granularity: 'grapheme',
  });
  const text = 'A👨‍👩‍👧‍👦e\u0301';
  const segments = [...segmenter.segment(text)];

  assert.deepEqual(segments.map(({ segment }) => segment), [
    'A',
    '👨‍👩‍👧‍👦',
    'é',
  ]);
  assert.deepEqual(segments.map(({ index }) => index), [0, 1, 12]);
});

test('word Segmenter 标记 word-like 片段并保留标点和空格', () => {
  const segmenter = new Intl.Segmenter('en-US', {
    granularity: 'word',
  });
  const segments = [...segmenter.segment('Hello, world!')];

  assert.deepEqual(
    segments.filter(({ isWordLike }) => isWordLike).map(({ segment }) => segment),
    ['Hello', 'world'],
  );
  assert.equal(segments.map(({ segment }) => segment).join(''), 'Hello, world!');
});

test('ListFormat 处理连接词和 locale 标点', () => {
  const conjunction = new Intl.ListFormat('en-US', {
    style: 'long',
    type: 'conjunction',
  });
  const disjunction = new Intl.ListFormat('en-US', {
    style: 'short',
    type: 'disjunction',
  });

  assert.equal(conjunction.format(['Python', 'C++', 'Node.js']), 'Python, C++, and Node.js');
  assert.equal(disjunction.format(['red', 'blue']), 'red or blue');

  const parts = conjunction.formatToParts(['a', 'b']);
  assert.equal(parts.map(({ value }) => value).join(''), 'a and b');
});

test('DisplayNames 把标准代码转成面向用户的名称', () => {
  const languages = new Intl.DisplayNames('zh-CN', { type: 'language' });
  const regions = new Intl.DisplayNames('en-US', { type: 'region' });
  const currencies = new Intl.DisplayNames('en-US', { type: 'currency' });

  assert.equal(languages.of('en'), '英语');
  assert.equal(regions.of('CN'), 'China');
  assert.equal(currencies.of('USD'), 'US Dollar');

  const codeFallback = new Intl.DisplayNames('en-US', {
    fallback: 'code',
    type: 'region',
  });
  assert.equal(codeFallback.of('ZZ'), 'Unknown Region');
});

test('supportedValuesOf 枚举当前实现支持的标准化值', () => {
  const calendars = Intl.supportedValuesOf('calendar');
  const currencies = Intl.supportedValuesOf('currency');
  const timeZones = Intl.supportedValuesOf('timeZone');

  assert.ok(calendars.includes('gregory'));
  assert.ok(currencies.includes('USD'));
  assert.ok(timeZones.includes('Asia/Shanghai'));
  assert.equal(new Set(calendars).size, calendars.length);
});
