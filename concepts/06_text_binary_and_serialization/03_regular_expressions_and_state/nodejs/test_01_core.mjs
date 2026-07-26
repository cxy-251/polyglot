// 正则表达式、捕获与状态。
// 共同问题：全串匹配与搜索如何区分；捕获组如何读取；替换回调获得什么；
// 复用正则对象是否携带可变游标。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/nodejs/language/test_014_regular_expressions_flags_state_captures_and_replacement.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('锚点表达全串匹配，普通 exec 搜索子串', () => {
  assert.equal(/\d+/.exec('id=12')[0], '12');
  assert.equal(/^\d+$/.test('12'), true);
  assert.equal(/^\d+$/.test('id=12'), false);
});

test('编号与命名捕获同时可读', () => {
  const match = /(?<name>[a-z]+)-(\d+)/.exec('item-12');

  assert.equal(match[1], 'item');
  assert.equal(match[2], '12');
  assert.equal(match.groups.name, 'item');
});

test('替换回调获得捕获、偏移和原字符串', () => {
  const calls = [];
  const result = 'a2'.replace(/(\d)/, (whole, digit, offset, source) => {
    calls.push({ whole, digit, offset, source });
    return String(Number(digit) * 2);
  });

  assert.equal(result, 'a4');
  assert.deepEqual(calls, [{ whole: '2', digit: '2', offset: 1, source: 'a2' }]);
});

test('global 正则复用时会修改 lastIndex', () => {
  const pattern = /\d/g;

  assert.equal(pattern.test('1'), true);
  assert.equal(pattern.lastIndex, 1);
  assert.equal(pattern.test('1'), false);
  assert.equal(pattern.lastIndex, 0);
});

