// 错误链、抑制与聚合。
// 共同问题：包装错误如何保留原因；隐式上下文能否隐藏；多个失败如何携带；
// 清理失败与主体失败如何同时保留。
//
// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/nodejs/language/test_004_control_flow_completion_records_and_errors.mjs
// polyglot-related: languages/nodejs/language/test_027_explicit_resource_management_and_disposable_stacks.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('Error cause 显式保留被包装的失败', () => {
  const original = new TypeError('invalid input');
  const wrapped = new Error('load failed', { cause: original });

  assert.equal(wrapped.cause, original);
  assert.equal(wrapped.message, 'load failed');
});

test('普通 catch 后抛出新错误不会自动建立隐式上下文', () => {
  let wrapped;
  try {
    throw new Error('original');
  } catch {
    wrapped = new Error('replacement');
  }

  assert.equal(wrapped.cause, undefined);

  // JavaScript 没有 Python __context__ 的自动链；需要用 Error options 明确传入 cause。
});

test('AggregateError 保存多个失败并仍是 Error', () => {
  const failures = [new Error('first'), new TypeError('second')];
  const aggregate = new AggregateError(failures, 'batch failed');

  assert.equal(aggregate instanceof Error, true);
  assert.deepEqual([...aggregate.errors], failures);
  assert.equal(aggregate.message, 'batch failed');
});

test('using 同时遇到主体和清理错误时使用 SuppressedError', () => {
  const body = new Error('body');
  const cleanup = new Error('cleanup');

  assert.throws(() => {
    using resource = {
      [Symbol.dispose]() {
        throw cleanup;
      },
    };
    assert.ok(resource);
    throw body;
  }, (error) => {
    assert.equal(error instanceof SuppressedError, true);
    assert.equal(error.error, cleanup);
    assert.equal(error.suppressed, body);
    return true;
  });
});

