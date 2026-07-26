// polyglot-covers:
// - nodejs.language.using-and-symbol-dispose
// - nodejs.language.await-using-and-symbol-async-dispose
// - nodejs.language.disposal-lifo-and-abrupt-completion
// - nodejs.language.disposable-stack-use-adopt-defer-and-move
// - nodejs.language.async-disposable-stack
// - nodejs.language.suppressed-error

// 跨语言迁移提示：using / await using 依赖 Symbol.dispose 协议并按逆序清理；
// Python 对应 with 协议，C++ 对应 RAII 析构。JavaScript 垃圾回收不会自动调用这些清理钩子。

import assert from 'node:assert/strict';
import test from 'node:test';

class Resource {
  constructor(label, events) {
    this.label = label;
    this.events = events;
    events.push(`open:${label}`);
  }

  [Symbol.dispose]() {
    this.events.push(`close:${this.label}`);
  }
}

class AsyncResource {
  constructor(label, events) {
    this.label = label;
    this.events = events;
    events.push(`open:${label}`);
  }

  async [Symbol.asyncDispose]() {
    await Promise.resolve();
    this.events.push(`close:${this.label}`);
  }
}

test('using 在词法作用域退出时按后进先出调用 Symbol.dispose', () => {
  const events = [];

  {
    using first = new Resource('first', events);
    using second = new Resource('second', events);
    assert.equal(first.label, 'first');
    assert.equal(second.label, 'second');
    events.push('body');
  }

  assert.deepEqual(events, [
    'open:first',
    'open:second',
    'body',
    'close:second',
    'close:first',
  ]);
});

test('return 或 throw 等 abrupt completion 也会触发 using 清理', () => {
  const events = [];

  const returnEarly = () => {
    using resource = new Resource('return', events);
    return resource.label;
  };
  assert.equal(returnEarly(), 'return');

  const throwError = () => {
    using resource = new Resource('throw', events);
    throw new Error(resource.label);
  };
  assert.throws(throwError, /throw/);
  assert.deepEqual(events, [
    'open:return',
    'close:return',
    'open:throw',
    'close:throw',
  ]);
});

test('using 接受 nullish 空资源，其他值必须实现 dispose 协议', () => {
  {
    using nothing = null;
    using alsoNothing = undefined;
    assert.equal(nothing, null);
    assert.equal(alsoNothing, undefined);
  }

  assert.throws(() => {
    using invalid = {};
    return invalid;
  }, TypeError);
});

test('await using 等待异步清理后才完成外围 async 函数', async () => {
  const events = [];

  const work = async () => {
    await using resource = new AsyncResource('async', events);
    events.push(`body:${resource.label}`);
    return 'result';
  };

  assert.equal(await work(), 'result');
  assert.deepEqual(events, ['open:async', 'body:async', 'close:async']);
});

test('await using 也能退回同步 Symbol.dispose', async () => {
  const events = [];

  {
    await using resource = new Resource('sync fallback', events);
    events.push(`body:${resource.label}`);
  }

  assert.deepEqual(events, [
    'open:sync fallback',
    'body:sync fallback',
    'close:sync fallback',
  ]);
});

test('DisposableStack.use 注册资源并支持幂等 dispose', () => {
  const events = [];
  const stack = new DisposableStack();
  const first = stack.use(new Resource('first', events));
  const second = stack.use(new Resource('second', events));

  assert.equal(first.label, 'first');
  assert.equal(second.label, 'second');
  assert.equal(stack.disposed, false);

  stack.dispose();
  assert.equal(stack.disposed, true);
  stack.dispose();
  assert.deepEqual(events, [
    'open:first',
    'open:second',
    'close:second',
    'close:first',
  ]);
  assert.throws(() => stack.use({
    [Symbol.dispose]() {},
  }), ReferenceError);
});

test('adopt 为普通值提供清理，defer 注册无参数清理动作', () => {
  const events = [];
  const stack = new DisposableStack();

  const value = stack.adopt({ id: 7 }, (resource) => {
    events.push(`adopt:${resource.id}`);
  });
  stack.defer(() => events.push('defer'));

  assert.deepEqual(value, { id: 7 });
  stack.dispose();
  assert.deepEqual(events, ['defer', 'adopt:7']);
});

test('move 转移清理所有权并让原 stack 变为 disposed', () => {
  const events = [];
  const original = new DisposableStack();
  original.use(new Resource('owned', events));

  const moved = original.move();
  assert.equal(original.disposed, true);
  assert.equal(moved.disposed, false);
  assert.deepEqual(events, ['open:owned']);

  moved.dispose();
  assert.deepEqual(events, ['open:owned', 'close:owned']);
});

test('AsyncDisposableStack 按 LIFO 混合处理异步和同步资源', async () => {
  const events = [];
  const stack = new AsyncDisposableStack();

  stack.use(new AsyncResource('async', events));
  stack.use(new Resource('sync', events));
  stack.defer(async () => {
    await Promise.resolve();
    events.push('defer');
  });

  await stack.disposeAsync();
  assert.equal(stack.disposed, true);
  assert.deepEqual(events, [
    'open:async',
    'open:sync',
    'defer',
    'close:sync',
    'close:async',
  ]);
});

test('清理失败会用 SuppressedError 保留先前的异常', () => {
  const bodyError = new Error('body failed');
  const disposeError = new Error('dispose failed');

  const work = () => {
    using resource = {
      [Symbol.dispose]() {
        throw disposeError;
      },
    };
    assert.ok(resource);
    throw bodyError;
  };

  assert.throws(work, (error) => {
    assert.equal(error instanceof SuppressedError, true);
    assert.equal(error.error, disposeError);
    assert.equal(error.suppressed, bodyError);
    return true;
  });
});
