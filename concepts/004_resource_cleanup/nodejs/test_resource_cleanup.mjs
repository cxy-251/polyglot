// 横向概念 004｜同步资源清理、异常安全与清理冲突。
// 共同问题：正常退出是否清理；异常退出是否清理；多个资源是否逆序清理；
// 清理由什么机制触发；清理失败与原始异常如何交互。
//
// polyglot-concept: resource_cleanup
// polyglot-related: languages/nodejs/language/test_027_explicit_resource_management_and_disposable_stacks.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class RecordingResource {
  constructor(name, events, cleanupError = undefined) {
    this.name = name;
    this.events = events;
    this.cleanupError = cleanupError;
    events.push(`acquire:${name}`);
  }

  [Symbol.dispose]() {
    this.events.push(`release:${this.name}`);
    if (this.cleanupError !== undefined) {
      throw this.cleanupError;
    }
  }
}

test('using 在正常离开词法作用域时调用 Symbol.dispose', () => {
  const events = [];

  {
    using resource = new RecordingResource('normal', events);
    assert.equal(resource.name, 'normal');
    events.push('body');
  }

  assert.deepEqual(events, ['acquire:normal', 'body', 'release:normal']);
});

test('异常离开 using 作用域时仍先完成清理', () => {
  const events = [];
  const original = new Error('body failed');

  assert.throws(() => {
    using resource = new RecordingResource('exception', events);
    assert.equal(resource.name, 'exception');
    events.push('body');
    throw original;
  }, (error) => error === original);

  assert.deepEqual(events, ['acquire:exception', 'body', 'release:exception']);
});

test('DisposableStack 按注册的后进先出顺序清理资源', () => {
  const events = [];

  {
    using stack = new DisposableStack();
    stack.use(new RecordingResource('first', events));
    stack.use(new RecordingResource('second', events));
    events.push('body');
  }

  assert.deepEqual(events, [
    'acquire:first',
    'acquire:second',
    'body',
    'release:second',
    'release:first',
  ]);
});

test('Symbol.dispose 的返回值不能抑制代码块异常', () => {
  const original = new Error('body failed');

  assert.throws(() => {
    using resource = {
      [Symbol.dispose]() {
        return true;
      },
    };
    assert.ok(resource);
    throw original;
  }, (error) => error === original);

  // 与 Python __exit__ 不同，dispose 返回值被忽略；资源协议没有异常抑制通道。
});

test('清理错误与代码块错误组合为 SuppressedError', () => {
  const events = [];
  const bodyError = new Error('body failed');
  const cleanupError = new Error('cleanup failed');

  assert.throws(() => {
    using resource = new RecordingResource('failing', events, cleanupError);
    assert.equal(resource.name, 'failing');
    throw bodyError;
  }, (error) => {
    assert.equal(error instanceof SuppressedError, true);
    assert.equal(error.error, cleanupError);
    assert.equal(error.suppressed, bodyError);
    return true;
  });

  assert.deepEqual(events, ['acquire:failing', 'release:failing']);
});
