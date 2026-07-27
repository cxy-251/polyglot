// 重新抛出、诊断信息与完成方式竞争。
// 共同问题：重新抛出是否保留原对象和诊断起点；清理块产生 return 或 throw 时，
// 原有完成方式是否继续传播。
//
// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/nodejs/language/test_004_control_flow_completion_records_and_errors.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('重新 throw 保留 Error 对象和创建时的 stack', () => {
  const original = new Error('failed');
  const originalStack = original.stack;

  assert.throws(() => {
    try {
      throw original;
    } catch (error) {
      throw error;
    }
  }, (caught) => {
    assert.equal(caught, original);
    assert.equal(caught.stack, originalStack);
    return true;
  });
});

test('finally return 替换待传播的异常', () => {
  function replace() {
    try {
      throw new Error('hidden');
    } finally {
      return 'replacement';
    }
  }

  assert.equal(replace(), 'replacement');
});

test('finally throw 替换待返回的值', () => {
  function replace() {
    try {
      return 'hidden';
    } finally {
      throw new Error('replacement');
    }
  }

  assert.throws(replace, /replacement/);
});
