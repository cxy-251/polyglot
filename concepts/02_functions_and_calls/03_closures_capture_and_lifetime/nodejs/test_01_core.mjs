// 闭包捕获与生命周期。
// 共同问题：闭包捕获绑定还是值；循环创建的函数看到哪个变量；捕获状态能否修改；
// 外层调用结束后状态是否仍存活。
//
// polyglot-family: functions_and_calls
// polyglot-concept: closures_capture_and_lifetime
// polyglot-related: languages/nodejs/language/test_005_functions_parameters_arguments_and_closures.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('闭包让外层词法环境在函数返回后继续存活', () => {
  function makeCounter() {
    let count = 0;
    return () => ++count;
  }

  const counter = makeCounter();

  assert.equal(counter(), 1);
  assert.equal(counter(), 2);
});

test('闭包捕获可变绑定而不是创建时的值快照', () => {
  let value = 'before';
  const read = () => value;

  value = 'after';

  assert.equal(read(), 'after');
});

test('for 的 let 为每轮创建独立词法绑定', () => {
  const functions = [];
  for (let index = 0; index < 3; index += 1) {
    functions.push(() => index);
  }

  assert.deepEqual(functions.map((functionValue) => functionValue()), [0, 1, 2]);
});

test('函数参数可以显式保存创建时快照', () => {
  const snapshot = ((captured) => () => captured)('before');
  let source = 'before';
  const readBinding = () => source;

  source = 'after';

  assert.equal(snapshot(), 'before');
  assert.equal(readBinding(), 'after');
});
