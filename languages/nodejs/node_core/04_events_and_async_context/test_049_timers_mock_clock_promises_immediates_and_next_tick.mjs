// polyglot-covers:
// - nodejs.core.timers-timeout-interval-immediate-and-cancellation
// - nodejs.core.timers-ref-unref-refresh-and-dispose
// - nodejs.core.timers-promises-timeout-immediate-and-abort
// - nodejs.core.timers-promises-interval-async-iterator
// - nodejs.core.timers-scheduler-yield
// - nodejs.core.process-next-tick-arguments-and-order
// - nodejs.core.test-mock-timers

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  scheduler,
  setImmediate as immediate,
  setInterval as interval,
  setTimeout as delay,
} from 'node:timers/promises';

test('mock timers 让 timeout 按虚拟时钟到期而不实际等待', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });
  const events = [];
  const start = Date.now();

  const first = setTimeout(() => events.push(`first:${Date.now() - start}`), 10);
  setTimeout(() => events.push(`second:${Date.now() - start}`), 20);

  t.mock.timers.tick(9);
  assert.deepEqual(events, []);
  first.refresh();
  t.mock.timers.tick(10);
  assert.deepEqual(events, ['first:19']);
  t.mock.timers.tick(1);
  assert.deepEqual(events, ['first:19', 'second:20']);
});

test('clearTimeout 与 Symbol.dispose 都会取消尚未执行的 handle', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const events = [];
  const cleared = setTimeout(() => events.push('cleared'), 10);
  const disposed = setTimeout(() => events.push('disposed'), 10);

  clearTimeout(cleared);
  disposed[Symbol.dispose]();
  t.mock.timers.tick(10);

  assert.deepEqual(events, []);
  assert.equal(cleared.hasRef(), true);
  assert.equal(disposed[Symbol.dispose](), undefined);
});

test('interval 重复执行直到 clearInterval，tick 可一次推进多次', (t) => {
  t.mock.timers.enable({ apis: ['setInterval'] });
  const events = [];
  const handle = setInterval(() => {
    events.push(events.length + 1);
    if (events.length === 3) {
      clearInterval(handle);
    }
  }, 5);

  t.mock.timers.tick(20);
  assert.deepEqual(events, [1, 2, 3]);
});

test('Immediate 在事件循环 check 阶段完成并可携带值', async () => {
  const events = [];
  const pending = immediate('value').then((value) => events.push(value));
  events.push('synchronous');

  assert.deepEqual(events, ['synchronous']);
  await pending;
  assert.deepEqual(events, ['synchronous', 'value']);
});

test('timers/promises delay 接受已取消 signal 并保留 cause', async () => {
  const reason = new Error('cancel timer');
  const signal = AbortSignal.abort(reason);

  await assert.rejects(
    delay(60_000, 'never', { signal }),
    (error) => error.name === 'AbortError' && error.cause === reason,
  );
});

test('timers/promises interval 是 async iterator，可由 signal 终止', async () => {
  const controller = new AbortController();
  const iterator = interval(0, 'tick', { signal: controller.signal });

  assert.deepEqual(await iterator.next(), { done: false, value: 'tick' });
  controller.abort();
  await assert.rejects(iterator.next(), (error) => error.name === 'AbortError');
});

test('scheduler.yield 把控制权交还事件循环后再恢复', async () => {
  const events = [];
  const work = async () => {
    events.push('before yield');
    await scheduler.yield();
    events.push('after yield');
  };

  const pending = work();
  events.push('caller');
  assert.deepEqual(events, ['before yield', 'caller']);
  await pending;
  assert.deepEqual(events, ['before yield', 'caller', 'after yield']);
});

test('process.nextTick 在当前栈清空后执行并支持附加参数', async () => {
  const events = [];
  const completed = new Promise((resolve) => {
    process.nextTick((first, second) => {
      events.push(`${first}:${second}`);
      resolve();
    }, 'next', 'tick');
  });
  events.push('synchronous');

  assert.deepEqual(events, ['synchronous']);
  await completed;
  assert.deepEqual(events, ['synchronous', 'next:tick']);
});

test('Timeout/Immediate 的 ref 状态只影响进程存活，不改变是否可取消', () => {
  const timeout = setTimeout(() => undefined, 60_000);
  const immediateHandle = setImmediate(() => undefined);

  try {
    assert.equal(timeout.hasRef(), true);
    assert.equal(timeout.unref(), timeout);
    assert.equal(timeout.hasRef(), false);
    assert.equal(timeout.ref(), timeout);

    assert.equal(immediateHandle.unref(), immediateHandle);
    assert.equal(immediateHandle.hasRef(), false);
  } finally {
    clearTimeout(timeout);
    clearImmediate(immediateHandle);
  }
});
