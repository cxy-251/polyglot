// 包解析、导出与可见性。
// 共同问题：包名如何解析到文件；包入口如何组织公共 API；私有名称是否强制隐藏；
// 相对导入以什么为基准。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/nodejs/language/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs

import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

test('package exports 只公开声明的入口和子路径', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-package-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, 'node_modules', 'demo'), { recursive: true });
  const packageRoot = join(root, 'node_modules', 'demo');
  await writeFile(join(packageRoot, 'package.json'), JSON.stringify({
    name: 'demo',
    type: 'module',
    exports: { '.': './index.mjs', './feature': './feature.mjs' },
  }));
  await writeFile(join(packageRoot, 'index.mjs'), 'export const value = 1;\n');
  await writeFile(join(packageRoot, 'feature.mjs'), 'export const feature = 2;\n');
  await writeFile(join(packageRoot, 'private.mjs'), 'export const hidden = 3;\n');
  const entry = join(root, 'entry.mjs');
  await writeFile(entry, "export { value } from 'demo'; export { feature } from 'demo/feature';\n");

  const namespace = await import(pathToFileURL(entry));
  assert.deepEqual({ ...namespace }, { feature: 2, value: 1 });

  const privateEntry = join(root, 'private-entry.mjs');
  await writeFile(privateEntry, "import 'demo/private.mjs';\n");
  await assert.rejects(import(pathToFileURL(privateEntry)), { code: 'ERR_PACKAGE_PATH_NOT_EXPORTED' });
});

test('相对说明符以当前模块 URL 为基准', () => {
  const resolved = new URL('./fixture.mjs', import.meta.url);

  assert.equal(resolved.protocol, 'file:');
  assert.equal(resolved.pathname.endsWith('/fixture.mjs'), true);
});

test('node: 前缀显式选择内置模块', async () => {
  const namespace = await import('node:path');

  assert.equal(typeof namespace.join, 'function');
  assert.equal(import.meta.resolve('node:path'), 'node:path');
});
