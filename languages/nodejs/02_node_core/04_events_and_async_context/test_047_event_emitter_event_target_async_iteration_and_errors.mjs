// polyglot-covers:
// - nodejs.core.events-emitter-on-once-prepend-and-this
// - nodejs.core.events-listener-mutation-during-emit
// - nodejs.core.events-error-error-monitor-and-capture-rejections
// - nodejs.core.events-once-promise-and-abort
// - nodejs.core.events-on-async-iterator-and-watermarks
// - nodejs.core.events-event-target-introspection
// - nodejs.core.events-add-abort-listener-and-max-listeners

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  EventEmitter,
  addAbortListener,
  errorMonitor,
  getEventListeners,
  getMaxListeners,
  on,
  once,
  setMaxListeners,
} from 'node:events';

test('emit 同步按注册顺序调用监听器，并返回是否存在监听器', () => {
  const emitter = new EventEmitter();
  const events = [];

  emitter.on('value', function (value) {
    events.push(`ordinary:${value}:${this === emitter}`);
  });
  emitter.prependListener('value', (value) => events.push(`prepended:${value}`));

  assert.equal(emitter.emit('value', 7), true);
  assert.equal(emitter.emit('missing'), false);
  assert.deepEqual(events, ['prepended:7', 'ordinary:7:true']);

  // 普通监听器的 this 是 emitter；箭头函数仍使用词法 this。
});

test('once 只执行一次，rawListeners 可观察内部 wrapper', () => {
  const emitter = new EventEmitter();
  let calls = 0;
  const listener = () => {
    calls += 1;
  };
  emitter.once('ready', listener);

  assert.deepEqual(emitter.listeners('ready'), [listener]);
  assert.notEqual(emitter.rawListeners('ready')[0], listener);
  assert.equal(emitter.rawListeners('ready')[0].listener, listener);

  emitter.emit('ready');
  emitter.emit('ready');
  assert.equal(calls, 1);
  assert.equal(emitter.listenerCount('ready'), 0);
});

test('emit 开始后使用监听器数组快照，本轮移除不跳过已排队监听器', () => {
  const emitter = new EventEmitter();
  const events = [];
  const second = () => events.push('second');
  const first = () => {
    events.push('first');
    emitter.removeListener('value', second);
  };

  emitter.on('value', first);
  emitter.on('value', second);
  emitter.emit('value');
  emitter.emit('value');

  assert.deepEqual(events, ['first', 'second', 'first']);
});

test('newListener 在加入前触发，removeListener 在移除后触发', () => {
  const emitter = new EventEmitter();
  const events = [];
  const listener = () => undefined;

  emitter.on('newListener', (name) => {
    if (name === 'value') {
      events.push(`before add:${emitter.listenerCount('value')}`);
    }
  });
  emitter.on('removeListener', (name) => {
    if (name === 'value') {
      events.push(`after remove:${emitter.listenerCount('value')}`);
    }
  });

  emitter.on('value', listener);
  emitter.off('value', listener);
  assert.deepEqual(events, ['before add:0', 'after remove:0']);
});

test('没有 error listener 时 emit error 会同步抛出该错误', () => {
  const emitter = new EventEmitter();
  const failure = new Error('failed');

  assert.throws(() => emitter.emit('error', failure), (error) => error === failure);

  const handled = [];
  emitter.on('error', (error) => handled.push(error.message));
  assert.equal(emitter.emit('error', failure), true);
  assert.deepEqual(handled, ['failed']);
});

test('errorMonitor 先观察错误，但不能代替普通 error listener', () => {
  const emitter = new EventEmitter();
  const events = [];
  emitter.on(errorMonitor, (error) => events.push(`monitor:${error.message}`));
  emitter.on('error', (error) => events.push(`handler:${error.message}`));

  emitter.emit('error', new Error('failure'));
  assert.deepEqual(events, ['monitor:failure', 'handler:failure']);

  const unhandled = new EventEmitter();
  unhandled.on(errorMonitor, () => events.push('observed only'));
  assert.throws(() => unhandled.emit('error', new Error('still unhandled')));
});

test('captureRejections 把 async listener 的拒绝转发为 error', async () => {
  const emitter = new EventEmitter({ captureRejections: true });
  const failure = new Error('async failure');
  const observed = once(emitter, 'error');

  emitter.on('work', async () => {
    throw failure;
  });
  emitter.emit('work');

  assert.deepEqual(await observed, [failure]);
  // error listener 自身不应是会拒绝的 async 函数，否则可能形成错误循环。
});

test('events.once 返回包含全部事件参数的 Promise', async () => {
  const emitter = new EventEmitter();
  const ready = once(emitter, 'ready');

  queueMicrotask(() => emitter.emit('ready', 1, 'second'));
  assert.deepEqual(await ready, [1, 'second']);
  assert.equal(emitter.listenerCount('ready'), 0);
});

test('once 默认把先到的 error 当拒绝，等待 error 本身时则正常完成', async () => {
  const emitter = new EventEmitter();
  const failure = new Error('failed');
  const waitingForData = once(emitter, 'data');
  queueMicrotask(() => emitter.emit('error', failure));
  await assert.rejects(waitingForData, (error) => error === failure);

  const waitingForError = once(emitter, 'error');
  queueMicrotask(() => emitter.emit('error', failure));
  assert.deepEqual(await waitingForError, [failure]);
});

test('once 接受 AbortSignal，并在取消时清理临时监听器', async () => {
  const emitter = new EventEmitter();
  const controller = new AbortController();
  const pending = once(emitter, 'ready', { signal: controller.signal });

  assert.equal(emitter.listenerCount('ready'), 1);
  controller.abort(new Error('cancelled'));
  await assert.rejects(
    pending,
    (error) => error.name === 'AbortError' && error.cause === controller.signal.reason,
  );
  assert.equal(emitter.listenerCount('ready'), 0);
});

test('events.on 把重复事件转成 async iterator 并在退出时移除监听器', async () => {
  const emitter = new EventEmitter();
  const controller = new AbortController();
  const iterator = on(emitter, 'value', { signal: controller.signal });

  emitter.emit('value', 1, 'first');
  emitter.emit('value', 2, 'second');
  assert.deepEqual((await iterator.next()).value, [1, 'first']);
  assert.deepEqual((await iterator.next()).value, [2, 'second']);

  controller.abort();
  await assert.rejects(iterator.next(), (error) => error.name === 'AbortError');
  assert.equal(emitter.listenerCount('value'), 0);
});

test('getEventListeners 同时支持 EventEmitter 和 EventTarget', () => {
  const emitter = new EventEmitter();
  const target = new EventTarget();
  const listener = () => undefined;

  emitter.on('value', listener);
  target.addEventListener('value', listener);

  assert.deepEqual(getEventListeners(emitter, 'value'), [listener]);
  assert.deepEqual(getEventListeners(target, 'value'), [listener]);
  assert.notEqual(getEventListeners(emitter, 'value'), emitter.listeners('value'));
});

test('setMaxListeners 可同时配置 emitter 与 EventTarget 而不添加监听器', () => {
  const emitter = new EventEmitter();
  const target = new EventTarget();

  setMaxListeners(20, emitter, target);
  assert.equal(getMaxListeners(emitter), 20);
  assert.equal(getMaxListeners(target), 20);
  assert.equal(emitter.listenerCount('value'), 0);
  assert.deepEqual(getEventListeners(target, 'value'), []);
});

test('addAbortListener 不会被 stopImmediatePropagation 阻止，并可显式 dispose', () => {
  const controller = new AbortController();
  const events = [];
  controller.signal.addEventListener('abort', (event) => {
    events.push('ordinary');
    event.stopImmediatePropagation();
  });
  const disposable = addAbortListener(
    controller.signal,
    () => events.push('protected'),
  );

  controller.abort();
  assert.deepEqual(events, ['ordinary', 'protected']);
  disposable[Symbol.dispose]();

  const second = new AbortController();
  const removed = addAbortListener(second.signal, () => events.push('removed'));
  removed[Symbol.dispose]();
  second.abort();
  assert.deepEqual(events, ['ordinary', 'protected']);
});
