// 作用域、名称查找与遮蔽。
// 共同问题：块是否创建作用域；内层绑定如何遮蔽外层名称；函数如何修改外层状态；
// 读取尚未初始化的局部名称在何处失败。
//
// polyglot-family: functions_and_calls
// polyglot-concept: scope_name_lookup_and_shadowing
// polyglot-related: languages/nodejs/language/test_002_lexical_grammar_bindings_scope_and_destructuring.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('let 和 const 属于块作用域，var 属于函数作用域', () => {
  let lexical = 'outer';

  {
    let lexical = 'inner';
    var functionScoped = 'visible';
    assert.equal(lexical, 'inner');
  }

  assert.equal(lexical, 'outer');
  assert.equal(functionScoped, 'visible');
});

test('内层词法绑定遮蔽外层绑定但不会改写它', () => {
  const label = 'outer';

  function readLocal() {
    const label = 'local';
    return label;
  }

  assert.equal(readLocal(), 'local');
  assert.equal(label, 'outer');
});

test('闭包直接修改捕获的外层绑定，不需要 nonlocal 声明', () => {
  let state = 1;
  function update() {
    state = 2;
  }

  update();
  assert.equal(state, 2);
});

test('TDZ 让声明前读取词法绑定立即失败', () => {
  assert.throws(() => {
    const read = value;
    let value = 1;
    return read;
  }, ReferenceError);

  // var 的同类读取会得到 undefined；不能把声明提升理解为赋值也已执行。
});
