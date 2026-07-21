// polyglot-covers:
// - nodejs.core.async-local-storage-run-enter-with-exit-and-disable
// - nodejs.core.async-local-storage-bind-and-snapshot
// - nodejs.core.async-local-storage-default-value-and-name
// - nodejs.core.async-resource-run-in-async-scope-and-destroy
// - nodejs.core.async-resource-bind
// - nodejs.core.event-emitter-async-resource
// - nodejs.core.async-hooks-init-before-after-destroy

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  AsyncLocalStorage,
  AsyncResource,
  createHook,
  executionAsyncId,
} from 'node:async_hooks';
import { EventEmitterAsyncResource } from 'node:events';

test('run 为回调和其创建的异步操作传播 store，返回回调结果', async () => {
  const storage = new AsyncLocalStorage();
  assert.equal(storage.getStore(), undefined);

  const result = await storage.run({ requestId: 'request-1' }, async () => {
    assert.deepEqual(storage.getStore(), { requestId: 'request-1' });
    await Promise.resolve();
    assert.deepEqual(storage.getStore(), { requestId: 'request-1' });
    return 'completed';
  });

  assert.equal(result, 'completed');
  assert.equal(storage.getStore(), undefined);
});

test('嵌套 run 暂时替换 store，退出后恢复外层上下文', async () => {
  const storage = new AsyncLocalStorage();
  const observed = [];

  await storage.run('outer', async () => {
    observed.push(storage.getStore());
    await storage.run('inner', async () => {
      observed.push(storage.getStore());
      await Promise.resolve();
      observed.push(storage.getStore());
    });
    observed.push(storage.getStore());
  });

  assert.deepEqual(observed, ['outer', 'inner', 'inner', 'outer']);
});

test('enterWith 影响当前同步执行余下部分，事件监听器中应谨慎使用', () => {
  const storage = new AsyncLocalStorage();

  storage.enterWith({ id: 1 });
  assert.deepEqual(storage.getStore(), { id: 1 });
  storage.enterWith({ id: 2 });
  assert.deepEqual(storage.getStore(), { id: 2 });
  storage.disable();
  assert.equal(storage.getStore(), undefined);

  // enterWith 没有词法恢复边界；普通请求处理优先使用 run，减少上下文泄漏。
});

test('exit 在回调内临时离开当前 store，随后恢复', () => {
  const storage = new AsyncLocalStorage();
  const observed = [];

  storage.run('context', () => {
    observed.push(storage.getStore());
    storage.exit(() => observed.push(storage.getStore()));
    observed.push(storage.getStore());
  });

  assert.deepEqual(observed, ['context', undefined, 'context']);
});

test('defaultValue 与 name 为无活动上下文和诊断提供信息', () => {
  const defaultStore = { requestId: 'default' };
  const storage = new AsyncLocalStorage({
    defaultValue: defaultStore,
    name: 'request-context',
  });

  assert.equal(storage.name, 'request-context');
  assert.equal(storage.getStore(), defaultStore);
  storage.run({ requestId: 'actual' }, () => {
    assert.deepEqual(storage.getStore(), { requestId: 'actual' });
  });
  assert.equal(storage.getStore(), defaultStore);
});

test('snapshot 捕获当前上下文并让以后任意函数在其中运行', () => {
  const storage = new AsyncLocalStorage();
  const runCaptured = storage.run('captured', () => AsyncLocalStorage.snapshot());

  assert.equal(storage.getStore(), undefined);
  assert.equal(runCaptured(() => storage.getStore()), 'captured');

  storage.run('other', () => {
    assert.equal(storage.getStore(), 'other');
    assert.equal(runCaptured(() => storage.getStore()), 'captured');
    assert.equal(storage.getStore(), 'other');
  });
});

test('AsyncLocalStorage.bind 固定函数创建时的上下文', () => {
  const storage = new AsyncLocalStorage();
  const bound = storage.run('bound-context', () => AsyncLocalStorage.bind(
    () => storage.getStore(),
  ));

  assert.equal(bound(), 'bound-context');
  assert.equal(storage.run('caller-context', bound), 'bound-context');
});

test('AsyncResource.runInAsyncScope 以资源上下文和指定 this 调用函数', () => {
  const storage = new AsyncLocalStorage();
  const resource = storage.run('resource-context', () => new AsyncResource(
    'POLYGLOT_RESOURCE',
  ));
  const receiver = { value: 7 };

  const result = resource.runInAsyncScope(function (suffix) {
    return `${storage.getStore()}:${this.value}:${suffix}`;
  }, receiver, 'done');

  assert.equal(result, 'resource-context:7:done');
  resource.emitDestroy();
});

test('AsyncResource.bind 把回调绑定到资源 async scope', () => {
  const storage = new AsyncLocalStorage();
  const resource = storage.run('resource', () => new AsyncResource('BOUND_RESOURCE'));
  const bound = resource.bind(() => storage.getStore());

  assert.equal(bound(), 'resource');
  resource.emitDestroy();
});

test('EventEmitterAsyncResource 让监听器在 emitter 创建上下文执行', () => {
  const storage = new AsyncLocalStorage();
  const emitter = storage.run('emitter-context', () => new EventEmitterAsyncResource({
    name: 'PolyglotEmitter',
  }));
  const observed = [];
  emitter.on('value', () => observed.push(storage.getStore()));

  storage.run('caller-context', () => emitter.emit('value'));
  assert.deepEqual(observed, ['emitter-context']);
  assert.equal(typeof emitter.asyncId, 'number');
  emitter.emitDestroy();
});

test('createHook 可观察自定义 AsyncResource 的生命周期', async () => {
  const events = [];
  const targetIds = new Set();
  const hook = createHook({
    after(asyncId) {
      if (targetIds.has(asyncId)) events.push(`after:${asyncId}`);
    },
    before(asyncId) {
      if (targetIds.has(asyncId)) events.push(`before:${asyncId}`);
    },
    destroy(asyncId) {
      if (targetIds.has(asyncId)) events.push(`destroy:${asyncId}`);
    },
    init(asyncId, type, triggerAsyncId) {
      if (type === 'POLYGLOT_HOOK_RESOURCE') {
        targetIds.add(asyncId);
        events.push(`init:${asyncId}:${triggerAsyncId}`);
      }
    },
  });
  hook.enable();

  try {
    const triggerId = executionAsyncId();
    const resource = new AsyncResource('POLYGLOT_HOOK_RESOURCE');
    const id = resource.asyncId();
    resource.runInAsyncScope(() => undefined);
    resource.emitDestroy();
    await new Promise((resolve) => setImmediate(resolve));

    assert.equal(events[0], `init:${id}:${triggerId}`);
    assert.ok(events.includes(`before:${id}`));
    assert.ok(events.includes(`after:${id}`));
    assert.ok(events.includes(`destroy:${id}`));
  } finally {
    hook.disable();
  }

  // hook 回调中不能使用会继续创建异步资源的日志 API，否则可能递归触发 hook。
});
