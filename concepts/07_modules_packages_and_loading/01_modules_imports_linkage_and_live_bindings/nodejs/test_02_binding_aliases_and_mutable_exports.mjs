// 导入绑定、别名与可变导出对象。
// 共同问题：导入后读取的是源绑定还是本地值；共享对象的内部修改是否可见；
// 重新绑定与修改对象为何产生不同迁移结果。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/nodejs/language/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function moduleUrl(tag) {
  const source = [
    'export let value = 1;',
    'export const items = [];',
    "export function update() { value = 2; items.push('updated'); }",
  ].join('\n');
  return `data:text/javascript,${encodeURIComponent(source)}#${tag}`;
}

test('namespace 读取 live binding，解构值是本地快照', async () => {
  const namespace = await import(moduleUrl('snapshot'));
  const { value: copiedValue, items: aliasedItems } = namespace;

  namespace.update();

  assert.equal(namespace.value, 2);
  assert.equal(copiedValue, 1);
  assert.equal(aliasedItems, namespace.items);
  assert.deepEqual(aliasedItems, ['updated']);

  // 静态 import 的命名绑定是 live binding；这里的普通解构赋值不是 import 声明，
  // 因此 copiedValue 固定为 1。对象值仍按引用共享内部状态。
});
