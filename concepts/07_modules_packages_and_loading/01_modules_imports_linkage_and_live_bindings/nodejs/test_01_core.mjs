// 模块、导入、链接与绑定可见性。
// 共同问题：模块何时执行；导入得到模块还是值快照；命名空间如何隔离；
// 声明如何跨文件暴露。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/nodejs/language/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

const source = [
  'export let value = 1;',
  'export function increment() { value += 1; }',
  'export default value;',
].join('\n');
const moduleUrl = `data:text/javascript,${encodeURIComponent(source)}`;

test('ESM namespace 暴露只读 live binding', async () => {
  const namespace = await import(moduleUrl);

  assert.equal(namespace.value, 1);
  namespace.increment();
  assert.equal(namespace.value, 2);
  assert.throws(() => {
    namespace.value = 10;
  }, TypeError);
});

test('default 表达式导出保存导出时的值', async () => {
  const namespace = await import(moduleUrl);

  assert.equal(namespace.value, 2);
  assert.equal(namespace.default, 1);
});

test('相同 URL 复用同一个模块记录和 namespace', async () => {
  const first = await import(moduleUrl);
  const second = await import(moduleUrl);

  assert.equal(first, second);
  assert.equal(second.value, 2);
});

test('模块 namespace 是不可扩展的专用对象', async () => {
  const namespace = await import(moduleUrl);

  assert.equal(Object.isExtensible(namespace), false);
  assert.equal(Object.getPrototypeOf(namespace), null);
});
