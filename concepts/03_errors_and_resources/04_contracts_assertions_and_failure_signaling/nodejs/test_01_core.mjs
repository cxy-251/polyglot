// 契约、断言与失败信号。
// 共同问题：开发期断言与输入校验如何区分；哪些约束能在编译期表达；
// 调用方如何精确检查失败类型和内容。
//
// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/nodejs/language/test_004_control_flow_completion_records_and_errors.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function positivePort(value) {
  if (typeof value !== 'number') {
    throw new TypeError('port must be a number');
  }
  if (!Number.isInteger(value) || value <= 0) {
    throw new RangeError('port must be a positive integer');
  }
  return value;
}

test('assert 模块产生可检查的 AssertionError', () => {
  assert.throws(() => assert.equal(1, 2), (error) => {
    assert.equal(error.name, 'AssertionError');
    assert.equal(error.actual, 1);
    assert.equal(error.expected, 2);
    return true;
  });
});

test('公共输入校验使用 TypeError 与 RangeError', () => {
  assert.equal(positivePort(8080), 8080);
  assert.throws(() => positivePort('8080'), TypeError);
  assert.throws(() => positivePort(0), RangeError);
});

test('throws 可以同时检查构造器和稳定消息', () => {
  assert.throws(
    () => positivePort(-1),
    {
      name: 'RangeError',
      message: /positive integer/,
    },
  );
});

test('JavaScript 函数签名不会在调用前执行静态类型检查', () => {
  function add(left, right) {
    return left + right;
  }

  assert.equal(add(1, 2), 3);
  assert.equal(add('1', 2), '12');

  // 与 C++ concepts 不同，约束必须由运行时代码、TypeScript 或外部静态工具提供。
});
