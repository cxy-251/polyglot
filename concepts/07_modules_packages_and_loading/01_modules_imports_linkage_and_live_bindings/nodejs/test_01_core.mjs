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

function moduleUrl(tag, moduleSource = source) {
  return `data:text/javascript,${encodeURIComponent(moduleSource)}#${tag}`;
}

test('named export 是 live binding，default 表达式保存求值时的值', async () => {
  const namespace = await import(moduleUrl('live-and-default'));

  assert.equal(namespace.value, 1);
  assert.equal(namespace.default, 1);
  namespace.increment();
  assert.equal(namespace.value, 2);
  assert.equal(namespace.default, 1);
});

test('ESM namespace 属性不可重新赋值', async () => {
  const namespace = await import(moduleUrl('namespace-assignment'));

  assert.throws(() => {
    namespace.value = 10;
  }, TypeError);
});

test('相同 URL 复用模块记录和 namespace', async () => {
  const url = moduleUrl('same-url');
  const first = await import(url);
  first.increment();
  const second = await import(url);

  assert.equal(first, second);
  assert.equal(second.value, 2);
});

test('不同 URL 创建彼此隔离的模块记录', async () => {
  const first = await import(moduleUrl('first-url'));
  const second = await import(moduleUrl('second-url'));

  first.increment();

  assert.notEqual(first, second);
  assert.equal(first.value, 2);
  assert.equal(second.value, 1);
});

test('同一 URL 的模块初始化只执行一次', async (t) => {
  const counterKey = `__polyglot_module_count_${process.pid}_${Date.now()}`;
  t.after(() => {
    delete globalThis[counterKey];
  });
  const countingSource = [
    `globalThis[${JSON.stringify(counterKey)}] = (globalThis[${JSON.stringify(counterKey)}] ?? 0) + 1;`,
    `export const initializationCount = globalThis[${JSON.stringify(counterKey)}];`,
  ].join('\n');
  const url = moduleUrl('initialize-once', countingSource);

  const first = await import(url);
  const second = await import(url);

  assert.equal(first.initializationCount, 1);
  assert.equal(second.initializationCount, 1);
  assert.equal(globalThis[counterKey], 1);
});

test('模块 namespace 是不可扩展的专用对象', async () => {
  const namespace = await import(moduleUrl('namespace-shape'));

  assert.equal(Object.isExtensible(namespace), false);
  assert.equal(Object.getPrototypeOf(namespace), null);
});
