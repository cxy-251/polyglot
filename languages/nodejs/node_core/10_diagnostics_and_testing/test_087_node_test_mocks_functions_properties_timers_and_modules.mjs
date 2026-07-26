// polyglot-covers:
// - nodejs.core.node-test-mock-fn-call-records-result-error-stack-this-and-target
// - nodejs.core.node-test-mock-fn-implementation-once-times-reset-calls-and-restore
// - nodejs.core.node-test-mock-method-original-this-symbol-and-automatic-restore
// - nodejs.core.node-test-mock-getter-setter-and-accessor-descriptors
// - nodejs.core.node-test-mock-property-access-history-values-once-caveat-and-restore
// - nodejs.core.node-test-mock-tracker-restore-all-versus-reset-lifecycle
// - nodejs.core.node-test-mock-timers-enable-selected-apis-tick-clear-and-date-clock
// - nodejs.core.node-test-mock-timers-node-timers-promises-and-interval-iterator
// - nodejs.core.node-test-mock-timers-run-all-set-time-reset-and-dispose
// - nodejs.core.node-test-mock-module-experimental-flag-and-late-binding
// - nodejs.core.node-test-mock-module-esm-commonjs-json-and-builtin-exports
// - nodejs.core.node-test-mock-module-cache-option-and-restore

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import timers from 'node:timers';
import timersPromises from 'node:timers/promises';
import test from 'node:test';

test('mock.fn 记录返回、异常、调用位置、this 和构造目标', (t) => {
  const receiver = { factor: 3 };
  const multiply = t.mock.fn(function multiply(value) {
    return this.factor * value;
  });
  assert.equal(multiply.call(receiver, 4), 12);

  const call = multiply.mock.calls[0];
  assert.deepEqual(call.arguments, [4]);
  assert.equal(call.result, 12);
  assert.equal(call.error, undefined);
  assert.equal(call.this, receiver);
  assert.equal(call.target, undefined);
  assert.ok(call.stack instanceof Error);
  assert.match(
    call.stack.stack,
    /test_087_node_test_mocks_functions_properties_timers_and_modules/,
  );

  const failure = new Error('planned failure');
  const throwing = t.mock.fn(() => {
    throw failure;
  });
  assert.throws(() => throwing('input'), (error) => error === failure);
  assert.equal(throwing.mock.calls[0].error, failure);
  assert.equal(throwing.mock.calls[0].result, undefined);

  function Record(name) {
    this.name = name;
  }
  const MockRecord = t.mock.fn(Record);
  const record = new MockRecord('Ada');
  assert.ok(record instanceof Record);
  assert.equal(MockRecord.mock.calls[0].target, Record);
  assert.equal(MockRecord.mock.calls[0].this, record);
  // target 记录真正被构造的原函数，而不是包在外层、供测试代码调用的 mock proxy。
  // calls 是内部记录的浅副本；修改数组不会删掉真正的调用历史。
  MockRecord.mock.calls.length = 0;
  assert.equal(MockRecord.mock.callCount(), 1);
});

test('mock.fn 可临时替换实现、限定次数并独立清空调用记录', (t) => {
  const original = (value) => `original:${value}`;
  const temporary = (value) => `temporary:${value}`;
  const fn = t.mock.fn(original, temporary, { times: 2 });

  assert.equal(fn('a'), 'temporary:a');
  assert.equal(fn('b'), 'temporary:b');
  assert.equal(fn('c'), 'original:c');

  fn.mock.mockImplementation((value) => `changed:${value}`);
  fn.mock.mockImplementationOnce((value) => `once:${value}`);
  assert.equal(fn('d'), 'once:d');
  assert.equal(fn('e'), 'changed:e');
  assert.equal(fn.mock.callCount(), 5);

  fn.mock.resetCalls();
  assert.equal(fn.mock.callCount(), 0);
  assert.equal(fn('f'), 'changed:f');
  fn.mock.restore();
  assert.equal(fn('g'), 'original:g');
  // restore 只恢复实现，代理仍可调用并继续记录；resetCalls 才会清空历史。
  assert.equal(fn.mock.callCount(), 2);
});

test('mock.method 默认保留原实现和 this，也支持 symbol 方法及自动恢复次数', (t) => {
  const inspect = Symbol('inspect');
  const service = {
    prefix: 'real',
    format(value) {
      return `${this.prefix}:${value}`;
    },
    [inspect]() {
      return this.prefix;
    },
  };

  const format = t.mock.method(service, 'format');
  assert.equal(service.format('value'), 'real:value');
  assert.equal(format.mock.calls[0].this, service);

  const symbolMethod = t.mock.method(
    service,
    inspect,
    function mockInspect() {
      return `mock:${this.prefix}`;
    },
  );
  assert.equal(service[inspect](), 'mock:real');
  assert.equal(symbolMethod.mock.callCount(), 1);

  const expiring = {
    read() {
      return 'original';
    },
  };
  const temporary = t.mock.method(expiring, 'read', () => 'temporary', { times: 1 });
  assert.equal(expiring.read(), 'temporary');
  assert.equal(expiring.read(), 'original');
  assert.equal(temporary.mock.callCount(), 1);
  // times 到期后对象属性已恢复原方法，第二次调用不再经过代理，因此记录仍为一次。
});

test('mock.getter 与 mock.setter 分别替换访问器，且仍按函数调用记录', (t) => {
  let stored = 2;
  const readable = {
    get value() {
      return stored;
    },
  };
  const writable = {
    set value(next) {
      stored = next;
    },
  };

  const getter = t.mock.getter(readable, 'value', () => 40);
  const setter = t.mock.setter(writable, 'value', (next) => {
    stored = next * 2;
  });
  assert.equal(readable.value, 40);
  writable.value = 5;
  assert.equal(stored, 10);
  assert.equal(getter.mock.callCount(), 1);
  assert.deepEqual(setter.mock.calls[0].arguments, [5]);

  getter.mock.restore();
  setter.mock.restore();
  assert.equal(readable.value, 10);
  writable.value = 7;
  assert.equal(stored, 7);
});

test('mock.property 同时跟踪读取与写入，并揭示 once 值也会被写操作消耗', (t) => {
  const settings = { mode: 'real' };
  const property = t.mock.property(settings, 'mode', 'mock');

  assert.equal(settings.mode, 'mock');
  settings.mode = 'written';
  assert.equal(settings.mode, 'written');
  assert.deepEqual(
    property.mock.accesses.map(({ type, value }) => ({ type, value })),
    [
      { type: 'get', value: 'mock' },
      { type: 'set', value: 'written' },
      { type: 'get', value: 'written' },
    ],
  );
  assert.ok(property.mock.accesses.every(({ stack }) => stack instanceof Error));

  property.mock.resetAccesses();
  property.mock.mockImplementation('stable');
  property.mock.resetAccesses();
  property.mock.mockImplementationOnce('once');
  settings.mode = 'ignored-write';
  assert.equal(settings.mode, 'once');
  // get 与 set 共用访问序号：这里 once 被 set 消耗，并成为新的属性值。
  assert.equal(property.mock.accesses[0].type, 'set');
  assert.equal(property.mock.accesses[0].value, 'once');
  assert.ok(property.mock.accesses[0].stack instanceof Error);

  property.mock.restore();
  assert.equal(settings.mode, 'real');
});

test('restoreAll 保留 mock 上下文，reset 则让 tracker 放弃后续管理', (t) => {
  const original = () => 'original';
  const first = t.mock.fn(original, () => 'mocked');
  const second = t.mock.fn(original, () => 'mocked');
  assert.deepEqual([first(), second()], ['mocked', 'mocked']);

  t.mock.restoreAll();
  assert.deepEqual([first(), second()], ['original', 'original']);
  first.mock.mockImplementation(() => 'changed-after-restore');
  assert.equal(first(), 'changed-after-restore');

  t.mock.reset();
  first.mock.mockImplementation(() => 'detached');
  t.mock.restoreAll();
  assert.equal(first(), 'detached');
  // reset 后代理仍能用，但已脱离 tracker，所以后来 restoreAll 不会再触碰它。
});

test('mock timers 用 tick 同步推进 timeout、interval、clear 和 Date 共用时钟', (t) => {
  t.mock.timers.enable({
    apis: ['setTimeout', 'setInterval', 'Date'],
    now: new Date('2025-01-01T00:00:00.000Z'),
  });
  const events = [];
  const cancelled = setTimeout(() => events.push('cancelled'), 5);
  clearTimeout(cancelled);
  const interval = setInterval(() => events.push(`interval:${Date.now()}`), 10);
  setTimeout(() => events.push(`timeout:${Date.now()}`), 20);

  t.mock.timers.tick(10);
  assert.deepEqual(events, ['interval:1735689600010']);
  t.mock.timers.tick(10);
  clearInterval(interval);
  assert.deepEqual(new Set(events), new Set([
    'interval:1735689600010',
    'interval:1735689600020',
    'timeout:1735689600020',
  ]));
  assert.equal(Date.now(), Date.parse('2025-01-01T00:00:00.020Z'));
});

test('启用 timer API 会同时替换全局、node:timers 和 promises 对象上的方法', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setInterval'] });
  const calls = [];
  setTimeout(() => calls.push('global'), 10);
  timers.setTimeout(() => calls.push('module'), 10);
  const promised = timersPromises.setTimeout(10, 'promise');

  const iterator = timersPromises.setInterval(5, 'tick');
  const first = iterator.next();
  t.mock.timers.tick(5);
  assert.deepEqual(await first, { value: 'tick', done: false });
  await iterator.return();

  t.mock.timers.tick(5);
  assert.equal(await promised, 'promise');
  assert.deepEqual(calls, ['global', 'module']);
  // 已解构保存的 timer 函数不会被替换；应通过全局名或模块命名空间对象访问。
});

test('runAll 按到期时间清空 timeout，setTime 只改日期而不触发计时器', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'setImmediate', 'Date'], now: 100 });
  const events = [];
  setTimeout(() => events.push('late'), 30);
  setTimeout(() => events.push('early-a'), 10);
  setTimeout(() => events.push('early-b'), 10);
  setImmediate(() => events.push('immediate'));

  t.mock.timers.runAll();
  assert.deepEqual(events, ['immediate', 'early-a', 'early-b', 'late']);
  assert.equal(Date.now(), 130);

  t.mock.timers.reset();
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'], now: 100 });
  setTimeout(() => events.push('not-triggered-by-setTime'), 10);
  t.mock.timers.setTime(5_000);
  assert.equal(Date.now(), 5_000);
  assert.equal(events.includes('not-triggered-by-setTime'), false);
  // setTime 只改 Date 参考值；它不是 tick，不能用来宣告既有 timeout 已到期。
});

test('reset 与 Symbol.dispose 都会把被替换的计时 API 恢复成真实实现', (t) => {
  const realDate = globalThis.Date;
  const realTimeout = globalThis.setTimeout;

  t.mock.timers.enable({ apis: ['Date', 'setTimeout'], now: 0 });
  assert.equal(Date.now(), 0);
  assert.notEqual(globalThis.setTimeout, realTimeout);
  t.mock.timers.reset();
  assert.equal(globalThis.Date, realDate);
  assert.equal(globalThis.setTimeout, realTimeout);

  t.mock.timers.enable({ apis: ['Date'], now: 1 });
  assert.equal(Date.now(), 1);
  t.mock.timers[Symbol.dispose]();
  assert.equal(globalThis.Date, realDate);
});

test('mock.module 必须显式启用，并能模拟 ESM、CJS、JSON 与内置模块', () => {
  const childEnvironment = { ...process.env };
  // 嵌套启动 test runner 时不能继承父 runner 的私有 worker 通道标记。
  delete childEnvironment.NODE_TEST_CONTEXT;
  delete childEnvironment.NODE_TEST_WORKER_ID;
  const withoutFlag = spawnSync(
    process.execPath,
    [
      '--input-type=module',
      '--eval',
      "import { mock } from 'node:test'; mock.module('node:path', { exports: {} });",
    ],
    { encoding: 'utf8', env: childEnvironment },
  );
  assert.notEqual(withoutFlag.status, 0);
  assert.match(withoutFlag.stderr, /mock\.module is not a function|experimental-test-module-mocks/);

  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-module-mocks-'));
  const fixture = join(directory, 'module-mocks.test.mjs');
  writeFileSync(join(directory, 'dependency.mjs'), [
    "export const named = 'real-esm';",
    "export default { kind: 'real-esm' };",
  ].join('\n'));
  writeFileSync(
    join(directory, 'dependency.cjs'),
    "module.exports = { kind: 'real-cjs', named: 'real-cjs' };\n",
  );
  writeFileSync(join(directory, 'data.json'), '{"kind":"real-json"}\n');
  writeFileSync(fixture, String.raw`
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);

test('ESM mock 只影响注册以后取得的绑定，restore 后恢复真实模块', async (t) => {
  const dependency = new URL('./dependency.mjs', import.meta.url);
  const prior = await import(
    new URL('./dependency.mjs?loaded-before-mock', import.meta.url)
  );
  const context = t.mock.module(dependency, {
    exports: { default: { kind: 'mock-esm' }, named: 'mock-esm' },
  });
  const mocked = await import(dependency);
  assert.equal(prior.named, 'real-esm');
  assert.equal(mocked.named, 'mock-esm');
  assert.equal(mocked.default.kind, 'mock-esm');

  context.restore();
  const restored = await import(dependency);
  assert.equal(restored.named, 'real-esm');
});

test('CJS mock 的 default 成为 module.exports，cache=true 写入 require.cache', (t) => {
  const path = fileURLToPath(new URL('./dependency.cjs', import.meta.url));
  const replacement = { kind: 'mock-cjs' };
  const context = t.mock.module(path, {
    cache: true,
    exports: { default: replacement, named: 'copied-name' },
  });
  const mocked = require(path);
  assert.equal(mocked, replacement);
  assert.equal(mocked.named, 'copied-name');
  assert.equal(require.cache[path].exports, replacement);

  context.restore();
  delete require.cache[path];
  assert.equal(require(path).kind, 'real-cjs');
});

test('JSON module mock 使用 default export，且不读取文件中的原值', async (t) => {
  const url = new URL('./data.json', import.meta.url);
  t.mock.module(url, { exports: { default: { kind: 'mock-json' } } });
  const mocked = await import(url, { with: { type: 'json' } });
  assert.deepEqual(mocked.default, { kind: 'mock-json' });
});

test('内置模块可同时供应 ESM named export 与 CommonJS module.exports', async (t) => {
  const replacement = { kind: 'mock-path' };
  t.mock.module('node:path', {
    exports: { default: replacement, sep: 'mock-separator' },
  });
  const esm = await import('node:path');
  const cjs = require('node:path');
  assert.equal(esm.sep, 'mock-separator');
  assert.equal(cjs, replacement);
  assert.equal(cjs.sep, 'mock-separator');
});
`);

  try {
    const result = spawnSync(
      process.execPath,
      [
        '--no-warnings',
        '--experimental-test-module-mocks',
        '--test',
        '--test-reporter=tap',
        fixture,
      ],
      { encoding: 'utf8', env: childEnvironment },
    );
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.match(result.stdout, /1\.\.4/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
  // module mock 仍是 early-development API；子进程隔离既展示启动开关，也避免污染本文件。
});
