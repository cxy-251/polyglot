// 异常传播、匹配与重新抛出。
// 共同问题：抛出的值有什么类型约束；处理器如何匹配；重新抛出是否保留原对象；
// 清理和 finally 在传播路径上的顺序是什么。
//
// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/nodejs/language/test_004_control_flow_completion_records_and_errors.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class DomainError extends Error {}

test('catch 接收所有抛出值，类型匹配由处理器代码完成', () => {
  let caught;

  try {
    throw new DomainError('failed');
  } catch (error) {
    if (error instanceof DomainError) {
      caught = error.message;
    }
  }

  assert.equal(caught, 'failed');
});

test('重新 throw 保留同一个错误对象', () => {
  const original = new DomainError('failed');

  assert.throws(() => {
    try {
      throw original;
    } catch (error) {
      throw error;
    }
  }, (error) => error === original);
});

test('finally 在异常到达外层处理器前执行', () => {
  const events = [];

  try {
    try {
      events.push('body');
      throw new DomainError('failed');
    } finally {
      events.push('finally');
    }
  } catch {
    events.push('caught');
  }

  assert.deepEqual(events, ['body', 'finally', 'caught']);
});

test('JavaScript 可以抛出非 Error 值', () => {
  assert.throws(() => {
    throw 'failed';
  }, (value) => value === 'failed');

  // 这在语法上合法，但会丢失标准错误堆栈、cause 等诊断结构。
});

test('finally 的 return 会覆盖先前的异常完成', () => {
  function override() {
    try {
      throw new Error('hidden');
    } finally {
      return 'replacement';
    }
  }

  assert.equal(override(), 'replacement');
});

