// 可调用对象适配与偏应用。
// 共同问题：如何预绑定参数；包装器如何保留调用契约；如何统一不同 callable；
// 适配器是否复制还是引用状态。
//
// polyglot-family: functions_and_calls
// polyglot-concept: callable_adaptation_and_partial_application
// polyglot-related: languages/nodejs/language/test_005_functions_parameters_arguments_and_closures.mjs
// polyglot-related: languages/nodejs/language/test_006_this_arrow_functions_bind_and_invocation_context.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('bind 同时预绑定 this 和前置参数', () => {
  function describe(value, suffix) {
    return `${this.prefix}${value}${suffix}`;
  }
  const bracket = describe.bind({ prefix: '[' }, 'value');

  assert.equal(bracket(']'), '[value]');
  assert.equal(bracket.length, 1);
});

test('闭包可以实现不绑定 this 的偏应用', () => {
  const partial = (functionValue, ...prefix) =>
    (...suffix) => functionValue(...prefix, ...suffix);
  const add = (left, right) => left + right;

  assert.equal(partial(add, 2)(3), 5);
});

test('普通包装器不会自动保留名称、长度和自定义属性', () => {
  function original(left, right) {
    return left + right;
  }
  original.category = 'math';
  const wrapper = (...args) => original(...args);

  assert.equal(wrapper(2, 3), 5);
  assert.equal(wrapper.length, 0);
  assert.equal(wrapper.category, undefined);

  // JavaScript 没有 Python functools.wraps 的标准等价物，元数据需要有选择地显式复制。
});

test('预绑定对象参数仍共享同一个可变对象', () => {
  const options = { prefix: 'a' };
  const read = ({ prefix }) => prefix;
  const adapted = read.bind(undefined, options);

  options.prefix = 'b';

  assert.equal(adapted(), 'b');
});

