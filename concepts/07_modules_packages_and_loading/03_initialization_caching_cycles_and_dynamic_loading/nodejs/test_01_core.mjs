// 初始化、缓存、循环依赖与动态加载。
// 共同问题：模块初始化执行几次；缓存键是什么；循环导入看到什么状态；
// 运行期加载如何报告失败。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/nodejs/language/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('相同 URL 的 dynamic import 复用模块记录', async (t) => {
  const source = [
    'globalThis.__polyglotRuns=(globalThis.__polyglotRuns??0)+1;',
    'export const run=globalThis.__polyglotRuns;',
  ].join('');
  const url = `data:text/javascript,${source}`;
  delete globalThis.__polyglotRuns;
  t.after(() => {
    delete globalThis.__polyglotRuns;
  });

  const first = await import(url);
  const second = await import(url);

  assert.equal(first, second);
  assert.equal(first.run, 1);
});

test('查询参数形成不同缓存键', async () => {
  const source = 'export default import.meta.url';
  const base = `data:text/javascript,${encodeURIComponent(source)}`;

  const first = await import(`${base}#one`);
  const second = await import(`${base}#two`);

  assert.notEqual(first, second);
  assert.notEqual(first.default, second.default);
});

test('dynamic import 以 rejected Promise 报告加载失败', async () => {
  await assert.rejects(import('polyglot-missing-package'), { code: 'ERR_MODULE_NOT_FOUND' });
});

test('top-level await 延迟模块完成', async () => {
  const source = 'const value = await Promise.resolve(42); export { value };';
  const namespace = await import(`data:text/javascript,${encodeURIComponent(source)}`);

  assert.equal(namespace.value, 42);
});
