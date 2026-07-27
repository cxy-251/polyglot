// 零宽匹配、游标推进与编译失败。
// 共同问题：零宽成功如何避免无限迭代；复用 matcher 是否泄漏游标；
// 非法模式在什么阶段报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/nodejs/language/test_014_regular_expressions_flags_state_captures_and_replacement.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('matchAll 对零宽结果执行安全推进且不修改原 RegExp', () => {
  const pattern = /(?=.)/g;

  const matches = [...'ab'.matchAll(pattern)];

  assert.deepEqual(matches.map(({ index }) => index), [0, 1]);
  assert.deepEqual(matches.map((match) => match[0]), ['', '']);
  assert.equal(pattern.lastIndex, 0);
});

test('直接 exec 的零宽成功不会自动增加 lastIndex', () => {
  const pattern = /(?=a)/g;

  const first = pattern.exec('a');

  assert.equal(first.index, 0);
  assert.equal(pattern.lastIndex, 0);

  // 手写 while(exec) 必须在空匹配时自行推进，否则会无限循环；matchAll 和字符串算法
  // 使用规范的 AdvanceStringIndex 处理这一边界。
});

test('非法正则源在构造时抛 SyntaxError', () => {
  assert.throws(() => new RegExp('('), SyntaxError);
});
