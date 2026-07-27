// 资源部分取得失败与控制流退出。
// 共同问题：后续资源取得失败时已取得资源是否清理；return 是否绕过清理；
// 清理责任何时登记，尚未成功取得的资源是否参与释放。
//
// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/nodejs/language/test_027_explicit_resource_management_and_disposable_stacks.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class Resource {
  constructor(name, events) {
    this.name = name;
    this.events = events;
    events.push(`construct:${name}`);
  }

  [Symbol.dispose]() {
    this.events.push(`dispose:${this.name}`);
  }
}

function acquire(name, events, fail = false) {
  events.push(`acquire:${name}`);
  if (fail) {
    throw new Error(`cannot acquire ${name}`);
  }
  return new Resource(name, events);
}

test('后续取得失败时 DisposableStack 清理已登记资源', () => {
  const events = [];

  assert.throws(() => {
    using stack = new DisposableStack();
    stack.use(acquire('first', events));
    stack.use(acquire('second', events, true));
  }, /cannot acquire second/);

  assert.deepEqual(events, [
    'acquire:first',
    'construct:first',
    'acquire:second',
    'dispose:first',
  ]);

  // stack.use 只登记成功返回的资源；second 没有资源对象，first 则在异常退出时释放。
});

test('return 不会绕过 using 的词法作用域清理', () => {
  const events = [];

  function work() {
    using resource = new Resource('value', events);
    assert.equal(resource.name, 'value');
    events.push('return');
    return 42;
  }

  const result = work();

  assert.equal(result, 42);
  assert.deepEqual(events, ['construct:value', 'return', 'dispose:value']);
});
