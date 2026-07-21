// polyglot-covers:
// - nodejs.core.globals-global-and-global-this
// - nodejs.core.globals-module-scoped-commonjs-names
// - nodejs.core.globals-web-platform-apis
// - nodejs.core.abort-controller-signal-and-composition
// - nodejs.core.timer-handles-ref-unref-refresh-and-dispose
// - nodejs.core.set-immediate-and-microtask-order

import assert from 'node:assert/strict';
import test from 'node:test';

import { setImmediate as setImmediatePromise } from 'node:timers/promises';

test('global 是历史别名，globalThis 是跨环境标准入口', () => {
  assert.equal(global, globalThis);
  assert.equal(globalThis.global, globalThis);
  assert.equal(typeof process, 'object');
  assert.equal(typeof Buffer, 'function');

  const key = '__polyglot_global_test__';
  globalThis[key] = 7;
  try {
    assert.equal(global[key], 7);
  } finally {
    delete globalThis[key];
  }
});

test('__dirname 等 CommonJS 名称不是全局变量', () => {
  assert.equal(Object.hasOwn(globalThis, '__dirname'), false);
  assert.equal(Object.hasOwn(globalThis, '__filename'), false);
  assert.equal(Object.hasOwn(globalThis, 'require'), false);
  assert.equal(Object.hasOwn(globalThis, 'module'), false);

  // 它们由 CommonJS wrapper 注入；ESM 通过 import.meta 获取自身元数据。
});

test('Node 提供兼容 Web 的文本、URL、请求响应和流全局对象', async () => {
  const encoded = new TextEncoder().encode('中文');
  assert.equal(new TextDecoder().decode(encoded), '中文');

  const url = new URL('/path?value=1', 'https://example.test');
  assert.equal(url.href, 'https://example.test/path?value=1');

  const response = Response.json({ ok: true }, { status: 201 });
  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), { ok: true });

  assert.equal(typeof ReadableStream, 'function');
  assert.equal(typeof WritableStream, 'function');
  assert.equal(typeof fetch, 'function');
});

test('AbortController 只触发一次 abort 并保存任意 reason', () => {
  const controller = new AbortController();
  const events = [];
  const reason = new Error('cancelled');
  controller.signal.addEventListener('abort', () => events.push('abort'));

  controller.abort(reason);
  controller.abort(new Error('ignored'));

  assert.equal(controller.signal.aborted, true);
  assert.equal(controller.signal.reason, reason);
  assert.deepEqual(events, ['abort']);
  assert.throws(() => controller.signal.throwIfAborted(), (error) => error === reason);
});

test('AbortSignal.abort/any 创建已取消或组合信号', () => {
  const first = new AbortController();
  const second = new AbortController();
  const combined = AbortSignal.any([first.signal, second.signal]);

  const reason = Symbol('reason');
  second.abort(reason);
  assert.equal(combined.aborted, true);
  assert.equal(combined.reason, reason);

  const already = AbortSignal.abort('finished');
  assert.equal(already.aborted, true);
  assert.equal(already.reason, 'finished');
});

test('Timeout handle 可 ref/unref、refresh 并通过 dispose 取消', async () => {
  let called = false;
  const handle = setTimeout(() => {
    called = true;
  }, 60_000);

  assert.equal(handle.hasRef(), true);
  assert.equal(handle.unref(), handle);
  assert.equal(handle.hasRef(), false);
  assert.equal(handle.ref(), handle);
  assert.equal(handle.refresh(), handle);

  handle[Symbol.dispose]();
  await Promise.resolve();
  assert.equal(called, false);
});

test('Immediate handle 支持 ref/unref 和显式取消', async () => {
  let called = false;
  const handle = setImmediate(() => {
    called = true;
  });
  assert.equal(handle.hasRef(), true);
  handle.unref();
  assert.equal(handle.hasRef(), false);
  clearImmediate(handle);

  await setImmediatePromise();
  assert.equal(called, false);
});

test('queueMicrotask 先于下一轮 setImmediate 阶段运行', async () => {
  const events = [];
  const completed = new Promise((resolve) => {
    setImmediate(() => {
      events.push('immediate');
      resolve();
    });
  });
  queueMicrotask(() => events.push('microtask'));

  await completed;
  assert.deepEqual(events, ['microtask', 'immediate']);
});
