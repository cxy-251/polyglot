// 可调用对象绑定与调用上下文。
// 共同问题：成员函数如何获得接收者；提取函数后是否保留接收者；如何显式调用；
// 语言是否允许固定或替换调用上下文。
//
// polyglot-family: functions_and_calls
// polyglot-concept: callable_binding_and_invocation_context
// polyglot-related: languages/nodejs/language/test_006_this_arrow_functions_bind_and_invocation_context.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

const counter = {
  value: 10,
  add(amount) {
    return this.value + amount;
  },
};

test('成员调用以点号左侧对象作为 this', () => {
  assert.equal(counter.add(2), 12);
});

test('提取普通方法会丢失接收者', () => {
  const extracted = counter.add;

  assert.throws(() => extracted(2), TypeError);
  assert.equal(extracted.call({ value: 20 }, 2), 22);

  // ESM 是严格模式；普通调用的 this 为 undefined。Python bound method 不会发生这种丢失。
});

test('bind 固定接收者和前置参数', () => {
  const bound = counter.add.bind(counter, 5);

  assert.equal(bound(), 15);
  assert.equal(bound.call({ value: 100 }), 15);
});

test('箭头函数捕获外围 this，call 无法替换它', () => {
  const owner = {
    value: 10,
    makeReader() {
      return () => this.value;
    },
  };
  const read = owner.makeReader();

  assert.equal(read(), 10);
  assert.equal(read.call({ value: 20 }), 10);
});

