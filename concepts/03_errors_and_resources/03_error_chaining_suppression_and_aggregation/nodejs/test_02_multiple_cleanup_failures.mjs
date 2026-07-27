// 多个清理失败的保留方式。
// 共同问题：主体失败后多个清理也失败时，哪个错误成为最外层；其余失败如何保留；
// 没有内置聚合协议时如何显式保存全部结果。
//
// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/nodejs/language/test_027_explicit_resource_management_and_disposable_stacks.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function failingResource(name, events) {
  return {
    [Symbol.dispose]() {
      events.push(`dispose:${name}`);
      throw new Error(name);
    },
  };
}

test('多个 dispose 失败形成按清理顺序嵌套的 SuppressedError', () => {
  const events = [];
  const bodyError = new Error('body');

  assert.throws(() => {
    using stack = new DisposableStack();
    stack.use(failingResource('first', events));
    stack.use(failingResource('second', events));
    throw bodyError;
  }, (outer) => {
    assert.equal(outer instanceof SuppressedError, true);
    assert.equal(outer.error instanceof SuppressedError, true);
    assert.equal(outer.error.error.message, 'first');
    assert.equal(outer.error.suppressed.message, 'second');
    assert.equal(outer.suppressed, bodyError);
    return true;
  });

  assert.deepEqual(events, ['dispose:second', 'dispose:first']);

  // 多个 dispose 错误先按发生顺序嵌套，再作为外层 error 与 body completion 组合；
  // 它与 AggregateError 的扁平 errors 列表不是同一种结构。
});
