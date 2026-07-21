// polyglot-covers:
// - nodejs.language.esm-static-import-and-live-bindings
// - nodejs.language.esm-default-export-expression
// - nodejs.language.esm-re-export
// - nodejs.language.module-namespace-exotic-object
// - nodejs.language.dynamic-import-and-module-cache
// - nodejs.language.top-level-await
// - nodejs.language.import-attributes
// - nodejs.language.import-meta-url-and-resolve

import assert from 'node:assert/strict';
import test from 'node:test';

import initialCount, {
  count,
  increment,
  reset,
} from './fixtures/modules/counter.mjs';
import * as counterNamespace from './fixtures/modules/counter.mjs';
import reexportedDefault, {
  initialCount as reexportedInitial,
  liveCount,
} from './fixtures/modules/reexport.mjs';

test.beforeEach(() => {
  reset();
});

test('命名 import 是只读 live binding，default 表达式保存导出时的值', () => {
  assert.equal(count, 0);
  assert.equal(initialCount, 0);

  assert.equal(increment(), 1);
  assert.equal(count, 1);
  assert.equal(counterNamespace.count, 1);

  // export default count 导出表达式当时的结果；export { count as default } 才是 live binding。
  assert.equal(initialCount, 0);
  assert.throws(() => {
    counterNamespace.count = 100;
  }, TypeError);
});

test('re-export 保留原模块绑定，导入者不创建独立副本', () => {
  assert.equal(liveCount, 0);
  assert.equal(reexportedInitial, 0);
  assert.equal(reexportedDefault, 0);

  increment();
  assert.equal(liveCount, 1);
  assert.equal(counterNamespace.count, 1);
});

test('module namespace 是密封、null-prototype 且键按字典序排列的 exotic 对象', () => {
  assert.equal(Object.getPrototypeOf(counterNamespace), null);
  assert.equal(Object.isExtensible(counterNamespace), false);
  assert.equal(Object.isSealed(counterNamespace), true);
  assert.equal(Object.prototype.toString.call(counterNamespace), '[object Module]');
  assert.deepEqual(Object.keys(counterNamespace), [
    'count',
    'default',
    'increment',
    'reset',
  ]);

  const descriptor = Object.getOwnPropertyDescriptor(counterNamespace, 'count');
  assert.equal(descriptor.enumerable, true);
  assert.equal(descriptor.configurable, false);
  assert.equal(descriptor.writable, true);

  // 描述符 writable 为 true 是为了让导出模块更新 live binding；导入方的 [[Set]] 仍失败。
});

test('dynamic import 返回 Promise，同一 URL 复用相同模块记录和 namespace', async () => {
  const firstPending = import('./fixtures/modules/counter.mjs');
  assert.equal(firstPending instanceof Promise, true);

  const first = await firstPending;
  const second = await import('./fixtures/modules/counter.mjs');

  assert.equal(first, counterNamespace);
  assert.equal(second, first);
  assert.equal(first.count, 0);

  first.increment();
  assert.equal(count, 1);
});

test('top-level await 延迟依赖模块完成，import 得到最终 namespace', async () => {
  const namespace = await import('./fixtures/modules/top_level_await.mjs');

  assert.equal(namespace.ready, true);
  assert.deepEqual(namespace.events, ['module start', 'module resumed']);
});

test('JSON module 必须通过 import attribute 声明 type', async () => {
  const namespace = await import('./fixtures/modules/settings.json', {
    with: { type: 'json' },
  });

  assert.deepEqual(namespace.default, {
    mode: 'learning',
    version: 1,
  });

  await assert.rejects(
    import('./fixtures/modules/settings.json'),
    (error) => error.code === 'ERR_IMPORT_ATTRIBUTE_MISSING',
  );
});

test('import.meta.url 是当前模块 URL，resolve 解析而不加载目标', () => {
  assert.equal(import.meta.url.startsWith('file:'), true);
  assert.equal(
    import.meta.url.endsWith(
      '/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs',
    ),
    true,
  );

  const resolved = import.meta.resolve('./fixtures/modules/counter.mjs');
  assert.equal(resolved.startsWith('file:'), true);
  assert.equal(resolved.endsWith('/fixtures/modules/counter.mjs'), true);
});

test('导入说明符按 URL 解析，查询参数会形成不同缓存键', async () => {
  const ordinary = await import('./fixtures/modules/top_level_await.mjs');
  const queried = await import('./fixtures/modules/top_level_await.mjs?variant=1');

  assert.notEqual(ordinary, queried);
  assert.deepEqual(queried.events, ['module start', 'module resumed']);

  // 对 file/data URL，query 和 fragment 属于模块身份；滥用动态 query 会制造重复实例。
});
