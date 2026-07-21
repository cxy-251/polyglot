// polyglot-covers:
// - nodejs.core.diagnostics-channel-name-identity-and-symbol-name
// - nodejs.core.diagnostics-channel-synchronous-publish-and-message-identity
// - nodejs.core.diagnostics-channel-subscribe-unsubscribe-and-expensive-message-gating
// - nodejs.core.diagnostics-channel-run-stores-transform-and-async-context
// - nodejs.core.diagnostics-channel-tracing-channel-names-and-subscriptions
// - nodejs.core.diagnostics-channel-trace-sync-result-error-and-receiver
// - nodejs.core.diagnostics-channel-trace-promise-lifecycle
// - nodejs.core.diagnostics-channel-trace-callback-lifecycle

import assert from 'node:assert/strict';
import { AsyncLocalStorage } from 'node:async_hooks';
import {
  channel,
  hasSubscribers,
  subscribe,
  tracingChannel,
  unsubscribe,
} from 'node:diagnostics_channel';
import test from 'node:test';

let sequence = 0;

function uniqueName(topic) {
  sequence += 1;
  return `polyglot.${process.pid}.${topic}.${sequence}`;
}

function observeTracing(topic) {
  const trace = tracingChannel(uniqueName(topic));
  const observations = [];
  const subscribers = Object.fromEntries(
    ['start', 'end', 'asyncStart', 'asyncEnd', 'error'].map((event) => [
      event,
      (context) => {
        // 保存对象引用用于证明五个阶段共用上下文，同时保存当时的字段快照用于检查时序。
        observations.push({
          event,
          context,
          result: context.result,
          error: context.error,
        });
      },
    ]),
  );
  trace.subscribe(subscribers);
  return { trace, observations, subscribers };
}

test('同名字符串或同一 Symbol 得到缓存 Channel，不同 Symbol 描述相同也不会碰撞', () => {
  const name = uniqueName('identity');
  assert.equal(channel(name), channel(name));

  const firstSymbol = Symbol('private-channel');
  const secondSymbol = Symbol('private-channel');
  assert.equal(channel(firstSymbol), channel(firstSymbol));
  assert.notEqual(channel(firstSymbol), channel(secondSymbol));

  assert.equal(hasSubscribers(name), false);
  assert.equal(channel(name).publish({ ignored: true }), undefined);
  // Channel 按名称放进全局注册表；库作者应使用带包名的稳定名称，Symbol 适合私有协作。
});

test('publish 同步调用订阅者并原样传递消息对象和通道名', () => {
  const name = uniqueName('publish');
  const messages = [];
  const listener = (message, publishedName) => {
    messages.push({ message, publishedName });
    message.observed = true;
  };
  subscribe(name, listener);

  const message = { operation: 'parse' };
  const returnValue = channel(name).publish(message);
  assert.equal(returnValue, undefined);
  assert.deepEqual(messages, [{ message, publishedName: name }]);
  assert.equal(message.observed, true);
  assert.equal(unsubscribe(name, listener), true);
  assert.equal(unsubscribe(name, listener), false);
  // 发布不是事件队列：处理器会在 publish 返回前运行，也不会克隆或冻结 message。
});

test('hasSubscribers 可避免在无人消费时构造昂贵诊断消息', () => {
  const name = uniqueName('gating');
  const diagnosticChannel = channel(name);
  let constructions = 0;
  const publishDetails = () => {
    if (diagnosticChannel.hasSubscribers) {
      constructions += 1;
      diagnosticChannel.publish({ stack: new Error().stack });
    }
  };

  publishDetails();
  assert.equal(constructions, 0);

  const received = [];
  const listener = (message) => received.push(message);
  diagnosticChannel.subscribe(listener);
  assert.equal(hasSubscribers(name), true);
  publishDetails();
  assert.equal(constructions, 1);
  assert.equal(received.length, 1);
  assert.match(received[0].stack, /publishDetails/);
  assert.equal(diagnosticChannel.unsubscribe(listener), true);
  assert.equal(diagnosticChannel.unsubscribe(listener), false);
});

test('runStores 先转换上下文，再让发布、函数和后续异步任务共享该 store', async () => {
  const storage = new AsyncLocalStorage();
  const diagnosticChannel = channel(uniqueName('store'));
  const subscriberStores = [];
  const listener = () => subscriberStores.push(storage.getStore());
  diagnosticChannel.subscribe(listener);
  diagnosticChannel.bindStore(storage, (message) => ({
    span: message.span,
    parent: storage.getStore()?.span,
  }));

  const receiver = { prefix: 'handled:' };
  let continuation;
  storage.run({ span: 'root' }, () => {
    const result = diagnosticChannel.runStores(
      { span: 'child' },
      function handle(value) {
        assert.equal(this, receiver);
        assert.deepEqual(storage.getStore(), { span: 'child', parent: 'root' });
        continuation = Promise.resolve().then(() => storage.getStore());
        return this.prefix + value;
      },
      receiver,
      'value',
    );
    assert.equal(result, 'handled:value');
    assert.deepEqual(storage.getStore(), { span: 'root' });
  });

  assert.deepEqual(subscriberStores, [{ span: 'child', parent: 'root' }]);
  assert.deepEqual(await continuation, { span: 'child', parent: 'root' });
  assert.equal(diagnosticChannel.unbindStore(storage), true);
  assert.equal(diagnosticChannel.unbindStore(storage), false);
  assert.equal(diagnosticChannel.unsubscribe(listener), true);
  // runStores 返回后同步调用方恢复父 store，但内部创建的 Promise 仍继承 child。
});

test('TracingChannel 展开为五个命名通道，并要求用同一批函数取消订阅', () => {
  const name = uniqueName('trace-names');
  const trace = tracingChannel(name);
  assert.equal(trace.start, channel(`tracing:${name}:start`));
  assert.equal(trace.end, channel(`tracing:${name}:end`));
  assert.equal(trace.asyncStart, channel(`tracing:${name}:asyncStart`));
  assert.equal(trace.asyncEnd, channel(`tracing:${name}:asyncEnd`));
  assert.equal(trace.error, channel(`tracing:${name}:error`));
  assert.equal(trace.hasSubscribers, false);

  const subscribers = {
    start() {},
    end() {},
    asyncStart() {},
    asyncEnd() {},
    error() {},
  };
  trace.subscribe(subscribers);
  assert.equal(trace.hasSubscribers, true);
  assert.equal(trace.unsubscribe(subscribers), true);
  assert.equal(trace.unsubscribe(subscribers), false);
});

test('traceSync 保留 receiver/参数/返回值，并按 start-error-end 记录同步异常', () => {
  const success = observeTracing('sync-success');
  const receiver = { base: 40 };
  const context = { operation: 'add' };
  const result = success.trace.traceSync(
    function add(value) {
      assert.equal(this, receiver);
      return this.base + value;
    },
    context,
    receiver,
    2,
  );
  assert.equal(result, 42);
  assert.deepEqual(success.observations.map(({ event }) => event), ['start', 'end']);
  assert.equal(success.observations[0].result, undefined);
  assert.equal(success.observations[1].result, 42);
  assert.ok(success.observations.every(({ context: seen }) => seen === context));
  assert.equal(success.trace.unsubscribe(success.subscribers), true);

  const failure = observeTracing('sync-error');
  const expected = new Error('cannot complete');
  assert.throws(() => failure.trace.traceSync(() => {
    throw expected;
  }), (error) => error === expected);
  assert.deepEqual(
    failure.observations.map(({ event }) => event),
    ['start', 'error', 'end'],
  );
  assert.equal(failure.observations[1].error, expected);
  assert.equal(failure.observations[2].error, expected);
  assert.equal(failure.trace.unsubscribe(failure.subscribers), true);
});

test('tracePromise 区分返回 Promise 与 Promise 落定两个阶段', async () => {
  const { trace, observations, subscribers } = observeTracing('promise');
  const context = { operation: 'load' };
  const receiver = { prefix: 'item-' };
  const result = await trace.tracePromise(
    async function load(id) {
      assert.equal(this, receiver);
      await Promise.resolve();
      return this.prefix + id;
    },
    context,
    receiver,
    7,
  );

  assert.equal(result, 'item-7');
  assert.deepEqual(
    observations.map(({ event }) => event),
    ['start', 'end', 'asyncStart', 'asyncEnd'],
  );
  assert.equal(observations[1].result, undefined);
  assert.equal(observations[2].result, 'item-7');
  assert.ok(observations.every(({ context: seen }) => seen === context));
  assert.equal(trace.unsubscribe(subscribers), true);
});

test('traceCallback 包裹指定位置的 Node 风格回调，并把第二参数记录为 result', async () => {
  const { trace, observations, subscribers } = observeTracing('callback');
  const context = { operation: 'lookup' };
  const receiver = { prefix: 'user-' };
  let returnValue;
  const callbackResult = await new Promise((resolve) => {
    returnValue = trace.traceCallback(
      function lookup(id, callback) {
        assert.equal(this, receiver);
        queueMicrotask(() => callback(null, this.prefix + id));
        return 'scheduled';
      },
      1,
      context,
      receiver,
      9,
      (error, value) => resolve({ error, value }),
    );
  });

  assert.equal(returnValue, 'scheduled');
  assert.deepEqual(callbackResult, { error: null, value: 'user-9' });
  assert.deepEqual(
    observations.map(({ event }) => event),
    ['start', 'end', 'asyncStart', 'asyncEnd'],
  );
  assert.equal(observations[2].result, 'user-9');
  assert.ok(observations.every(({ context: seen }) => seen === context));
  assert.equal(trace.unsubscribe(subscribers), true);
  // traceCallback 默认认为最后一个参数是 callback；显式 position 可处理回调不在末尾的 API。
});
