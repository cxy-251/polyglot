// polyglot-covers:
// - nodejs.language.regexp-flags-and-unicode-modes
// - nodejs.language.regexp-global-sticky-and-last-index
// - nodejs.language.regexp-capturing-and-named-groups
// - nodejs.language.regexp-lookaround-and-backreferences
// - nodejs.language.regexp-match-search-match-all
// - nodejs.language.regexp-replacement-patterns
// - nodejs.language.regexp-escape
// - nodejs.language.regexp-unicode-sets

import assert from 'node:assert/strict';
import test from 'node:test';

test('常用 flag 改变大小写、多行、点号和 Unicode 解释', () => {
  assert.equal(/polyglot/i.test('POLYGLOT'), true);
  assert.equal(/^second$/m.test('first\nsecond\nthird'), true);
  assert.equal(/^first.*second$/s.test('first\nsecond'), true);

  const lightBulb = '💡';
  assert.equal(/^.$/.test(lightBulb), false);
  assert.equal(/^.$/u.test(lightBulb), true);
  assert.equal([...lightBulb.matchAll(/./gu)].length, 1);
});

test('global 与 sticky 正则使用可变 lastIndex', () => {
  const global = /\w+/g;
  assert.equal(global.exec('one two')[0], 'one');
  assert.equal(global.lastIndex, 3);
  assert.equal(global.exec('one two')[0], 'two');
  assert.equal(global.lastIndex, 7);
  assert.equal(global.exec('one two'), null);
  assert.equal(global.lastIndex, 0);

  const sticky = /\w+/y;
  sticky.lastIndex = 4;
  assert.equal(sticky.exec('one two')[0], 'two');
  sticky.lastIndex = 3;
  assert.equal(sticky.exec('one two'), null);
  assert.equal(sticky.lastIndex, 0);
});

test('复用 global test 时 lastIndex 会让结果看似交替', () => {
  const pattern = /item/g;

  assert.equal(pattern.test('item'), true);
  assert.equal(pattern.lastIndex, 4);
  assert.equal(pattern.test('item'), false);
  assert.equal(pattern.lastIndex, 0);

  // 只做存在性判断时避免无意复用带 g/y 的实例，或在每次输入前明确重置 lastIndex。
  assert.equal(/item/.test('item'), true);
  assert.equal(/item/.test('item'), true);
});

test('捕获组可以编号和命名，未参与的可选组为 undefined', () => {
  const pattern = /(?<year>\d{4})-(?<month>\d{2})(?:-(?<day>\d{2}))?/;
  const match = pattern.exec('date=2026-07');

  assert.equal(match[0], '2026-07');
  assert.deepEqual(match.slice(1), ['2026', '07', undefined]);
  assert.deepEqual({ ...match.groups }, {
    day: undefined,
    month: '07',
    year: '2026',
  });
  assert.equal(match.index, 5);
  assert.equal(match.input, 'date=2026-07');
});

test('反向引用要求后文重复同一文本，lookaround 不消费字符', () => {
  assert.equal(/\b(\w+)\s+\1\b/.test('very very clear'), true);
  assert.equal(/\b(\w+)\s+\1\b/.test('very clear'), false);

  assert.equal(/\d+(?= USD)/.exec('25 USD')[0], '25');
  assert.equal(/(?<=USD )\d+/.exec('USD 25')[0], '25');
  assert.equal(/foo(?!bar)/.test('foobaz'), true);
  assert.equal(/foo(?!bar)/.test('foobar'), false);
});

test('match 的返回形状受 global 影响，matchAll 保留每次捕获信息', () => {
  const text = 'x=1 y=20';

  assert.deepEqual(text.match(/\d+/g), ['1', '20']);
  const single = text.match(/(\w)=(\d+)/);
  assert.deepEqual(single.slice(0, 3), ['x=1', 'x', '1']);

  const all = [...text.matchAll(/(?<name>\w)=(?<value>\d+)/g)];
  assert.deepEqual(all.map((match) => ({
    index: match.index,
    name: match.groups.name,
    value: match.groups.value,
  })), [
    { index: 0, name: 'x', value: '1' },
    { index: 4, name: 'y', value: '20' },
  ]);

  assert.throws(() => [...text.matchAll(/\d+/)], TypeError);
});

test('replace 字符串支持特殊替换模式和命名组', () => {
  const input = 'Ada Lovelace';
  const pattern = /(?<first>\w+) (?<last>\w+)/;

  assert.equal(input.replace(pattern, '$<last>, $<first>'), 'Lovelace, Ada');
  assert.equal('abc'.replace(/b/, '[$&]-$`-$\''), 'a[b]-a-cc');

  // 替换字符串中的 $&、$`、$' 有特殊含义；动态字面文本更适合使用替换回调返回。
  assert.equal('price'.replace(/price/, () => '$&100'), '$&100');
});

test('RegExp.escape 把任意文本安全嵌入新正则', {
  skip: typeof RegExp.escape !== 'function',
}, () => {
  const userInput = 'file[1].txt';
  const unsafe = new RegExp(`^${userInput}$`);
  const safe = new RegExp(`^${RegExp.escape(userInput)}$`);

  assert.equal(unsafe.test(userInput), false);
  assert.equal(safe.test(userInput), true);
  assert.equal(safe.test('file1xtxt'), false);
});

test('Unicode sets v flag 支持字符串属性和集合运算', {
  skip: (() => {
    try {
      new RegExp('[\\p{ASCII}&&\\p{Letter}]', 'v');
      return false;
    } catch {
      return true;
    }
  })(),
}, () => {
  const asciiLetters = new RegExp('^[\\p{ASCII}&&\\p{Letter}]+$', 'v');
  assert.equal(asciiLetters.test('Polyglot'), true);
  assert.equal(asciiLetters.test('编程'), false);

  const nonAsciiDigits = new RegExp('^[\\p{Decimal_Number}--[0-9]]+$', 'v');
  assert.equal(nonAsciiDigits.test('１２３'), true);
  assert.equal(nonAsciiDigits.test('123'), false);
});
