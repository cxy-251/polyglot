// 横向概念 003｜参数绑定、对象传递与默认值。
// 共同问题：缺少或多余实参如何处理；修改与重新绑定是否影响调用者；
// 默认表达式何时求值；如何表达命名选项和可变参数。
//
// polyglot-family: functions_and_calls
// polyglot-concept: argument_passing
// polyglot-related: languages/nodejs/language/test_005_functions_parameters_arguments_and_closures.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('缺少实参得到 undefined，多余实参默认被忽略', () => {
  function pair(first, second) {
    return [first, second];
  }

  assert.deepEqual(pair('a'), ['a', undefined]);
  assert.deepEqual(pair('a', 'b', 'ignored'), ['a', 'b']);
});

test('对象引用按值传递：修改可见，参数重新赋值只影响局部绑定', () => {
  const original = ['before'];

  function mutateThenRebind(value) {
    value.push('mutated');
    value = ['replacement'];
    return value;
  }

  const replacement = mutateThenRebind(original);
  assert.deepEqual(original, ['before', 'mutated']);
  assert.deepEqual(replacement, ['replacement']);
});

test('默认表达式在每次缺少或传入 undefined 时重新求值', () => {
  let defaultCalls = 0;
  function create(value = { id: ++defaultCalls }) {
    return value;
  }

  const first = create();
  const second = create(undefined);

  assert.notEqual(first, second);
  assert.deepEqual([first.id, second.id], [1, 2]);
  assert.equal(create(null), null);
  assert.equal(defaultCalls, 2);
});

test('对象解构模拟具名选项，rest 参数收集多余位置实参', () => {
  function collect(required, { urgent = false } = {}, ...extra) {
    return { required, urgent, extra };
  }

  assert.deepEqual(collect('task', { urgent: true }, 1, 2), {
    required: 'task',
    urgent: true,
    extra: [1, 2],
  });

  // JavaScript 没有 Python 式关键字实参；这里传递的仍是普通位置对象。
});
