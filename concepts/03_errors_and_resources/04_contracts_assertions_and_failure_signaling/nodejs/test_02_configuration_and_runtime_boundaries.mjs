// 断言配置与运行时契约边界。
// 共同问题：开发断言能否被配置移除；类型约束是否检查运行时值；
// 公共 API 应采用什么稳定失败通道。
//
// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/nodejs/language/test_004_control_flow_completion_records_and_errors.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function positive(value) {
  if (typeof value !== 'number') {
    throw new TypeError('must be a number');
  }
  if (!Number.isInteger(value) || value <= 0) {
    throw new RangeError('must be a positive integer');
  }
  return value;
}

test('node:assert 是运行时函数而非可删除的语言语句', () => {
  assert.throws(
    () => assert.ok(false, 'broken invariant'),
    {
      name: 'AssertionError',
      message: /broken invariant/,
    },
  );

  // Node.js 没有与 Python -O 或 C++ NDEBUG 对应的语言级删除规则；打包器转换不属于
  // ECMAScript/Node 运行时保证。公共输入错误仍不应伪装成 AssertionError。
});

test('动态函数签名不替代运行时类型和值校验', () => {
  assert.equal(positive(2), 2);
  assert.throws(() => positive('2'), TypeError);
  assert.throws(() => positive(-2), RangeError);

  // TypeScript 可在外部构建阶段提供静态约束，但发给 Node.js 的 JavaScript 仍须保护
  // 不可信边界；正值约束也不是普通类型签名能够表达的运行时事实。
});
