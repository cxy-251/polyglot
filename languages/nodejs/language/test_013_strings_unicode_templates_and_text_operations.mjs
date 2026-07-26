// polyglot-covers:
// - nodejs.language.string-utf16-code-units-and-code-points
// - nodejs.language.string-iteration-and-well-formedness
// - nodejs.language.unicode-normalization
// - nodejs.language.string-search-slice-and-padding
// - nodejs.language.string-replace-and-replace-all
// - nodejs.language.template-literals-and-tagged-templates
// - nodejs.language.string-raw

import assert from 'node:assert/strict';
import test from 'node:test';

test('字符串 length 与索引按 UTF-16 code unit 计数', () => {
  const text = 'A💡B';

  assert.equal(text.length, 4);
  assert.equal(text[0], 'A');
  assert.equal(text[1], '\ud83d');
  assert.equal(text[2], '\udca1');
  assert.equal(text.codePointAt(1), 0x1f4a1);
  assert.equal(String.fromCodePoint(0x1f4a1), '💡');

  // charCodeAt 返回 code unit；codePointAt 才能在代理对起点读取完整 Unicode code point。
  assert.equal(text.charCodeAt(1), 0xd83d);
});

test('字符串迭代器按 code point 前进，但组合字素仍可能含多个 code point', () => {
  assert.deepEqual([...'A💡B'], ['A', '💡', 'B']);

  const family = '👨‍👩‍👧‍👦';
  assert.ok(family.length > 1);
  assert.ok([...family].length > 1);

  const segments = [...new Intl.Segmenter('zh-CN', {
    granularity: 'grapheme',
  }).segment(family)];
  assert.equal(segments.length, 1);
  assert.equal(segments[0].segment, family);
});

test('isWellFormed 与 toWellFormed 处理孤立代理项', () => {
  const loneHighSurrogate = '\ud83d';
  const completePair = '\ud83d\udca1';

  assert.equal(loneHighSurrogate.isWellFormed(), false);
  assert.equal(completePair.isWellFormed(), true);
  assert.equal(loneHighSurrogate.toWellFormed(), '\ufffd');
  assert.equal(completePair.toWellFormed(), '💡');
});

test('视觉相同文本可能由不同 code point 序列构成', () => {
  const composed = 'é';
  const decomposed = 'e\u0301';

  assert.notEqual(composed, decomposed);
  assert.equal(composed.length, 1);
  assert.equal(decomposed.length, 2);
  assert.equal(composed.normalize('NFC'), decomposed.normalize('NFC'));
  assert.equal(composed.normalize('NFD'), decomposed.normalize('NFD'));

  // 用户标识、搜索键或文件名是否规范化属于领域决策；不要在不理解外部协议时随意改变。
});

test('slice 支持负索引，substring 会交换边界并把负数当零', () => {
  const text = 'abcdef';

  assert.equal(text.slice(1, 4), 'bcd');
  assert.equal(text.slice(-3), 'def');
  assert.equal(text.slice(4, 1), '');

  assert.equal(text.substring(1, 4), 'bcd');
  assert.equal(text.substring(4, 1), 'bcd');
  assert.equal(text.substring(-3, 2), 'ab');
});

test('搜索、填充、重复和修剪返回新字符串', () => {
  const text = '  polyglot-node  ';

  assert.equal(text.includes('node'), true);
  assert.equal(text.startsWith('  poly'), true);
  assert.equal(text.endsWith('  '), true);
  assert.equal(text.trim(), 'polyglot-node');
  assert.equal('7'.padStart(3, '0'), '007');
  assert.equal('ab'.repeat(3), 'ababab');
  assert.throws(() => 'x'.repeat(-1), RangeError);
});

test('replace 默认只替换首个字符串匹配，replaceAll 替换全部', () => {
  const text = 'one one one';

  assert.equal(text.replace('one', 'two'), 'two one one');
  assert.equal(text.replaceAll('one', 'two'), 'two two two');
  assert.equal(text, 'one one one');

  assert.throws(() => text.replaceAll(/one/, 'two'), TypeError);
  assert.equal(text.replaceAll(/one/g, 'two'), 'two two two');
});

test('替换回调可读取匹配、捕获组、偏移和原字符串', () => {
  const seen = [];
  const result = 'Ada:42'.replace(
    /(?<name>[A-Za-z]+):(?<id>\d+)/,
    (match, name, id, offset, source, groups) => {
      // 命名组对象没有 Object.prototype，展开后再保存可获得便于比较的普通记录。
      assert.equal(Object.getPrototypeOf(groups), null);
      seen.push({ groups: { ...groups }, id, match, name, offset, source });
      return `${groups.id}-${groups.name.toLowerCase()}`;
    },
  );

  assert.equal(result, '42-ada');
  assert.deepEqual(seen, [{
    groups: { id: '42', name: 'Ada' },
    id: '42',
    match: 'Ada:42',
    name: 'Ada',
    offset: 0,
    source: 'Ada:42',
  }]);
});

test('模板字面量插值按表达式求值并执行字符串转换', () => {
  const name = 'Ada';
  const record = {
    toString() {
      return 'record';
    },
  };

  assert.equal(`hello ${name}, ${1 + 2}, ${record}`, 'hello Ada, 3, record');

  const multiline = `first
second`;
  assert.equal(multiline, 'first\nsecond');
});

test('tagged template 同时获得固定字符串片段和未经拼接的值', () => {
  let firstStrings;
  const tag = (strings, ...values) => {
    firstStrings ??= strings;
    return { strings, values };
  };
  const render = (name, count) => tag`name=${name}, count=${count}`;

  const first = render('Ada', 2);
  const second = render('Grace', 3);

  // 模板对象按语法位置缓存；反复执行 render 内同一个模板位置时会得到相同对象。
  assert.equal(first.strings, second.strings);
  assert.deepEqual([...first.strings], ['name=', ', count=', '']);
  assert.deepEqual(first.values, ['Ada', 2]);
  assert.equal(Object.isFrozen(first.strings), true);
  assert.equal(Object.isFrozen(first.strings.raw), true);
});

test('tag 可区分 cooked 与 raw 文本，String.raw 保留反斜杠', () => {
  const inspect = (strings) => ({
    cooked: strings[0],
    raw: strings.raw[0],
  });

  assert.deepEqual(inspect`line\nnext`, {
    cooked: 'line\nnext',
    raw: 'line\\nnext',
  });
  assert.equal(String.raw`C:\temp\file.txt`, 'C:\\temp\\file.txt');
});
