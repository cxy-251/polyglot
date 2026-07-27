// 解析、执行与相对基准。
// 共同问题：定位模块是否等于执行模块；相对说明符由什么上下文解释；
// 导出列表或命名约定是否构成真正访问控制。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/nodejs/language/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs

import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

test('相对说明符按 importing module 的 URL 解析而不是 cwd', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-relative-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const entry = join(root, 'nested', 'entry.mjs');
  await mkdir(dirname(entry), { recursive: true });
  await writeFile(join(root, 'value.mjs'), 'export const value = 42;\n');
  await writeFile(entry, "export { value } from '../value.mjs';\n");

  const namespace = await import(pathToFileURL(entry));

  assert.equal(namespace.value, 42);
});

test('package exports 限制包说明符但不是文件系统访问控制', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-exports-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const packageRoot = join(root, 'node_modules', 'demo');
  await mkdir(packageRoot, { recursive: true });
  await writeFile(
    join(packageRoot, 'package.json'),
    JSON.stringify({ name: 'demo', type: 'module', exports: './index.mjs' }),
  );
  await writeFile(join(packageRoot, 'index.mjs'), 'export const visible = 1;\n');
  await writeFile(join(packageRoot, 'private.mjs'), 'export const hidden = 2;\n');
  const blockedEntry = join(root, 'blocked.mjs');
  await writeFile(blockedEntry, "import 'demo/private.mjs';\n");

  await assert.rejects(
    import(pathToFileURL(blockedEntry)),
    { code: 'ERR_PACKAGE_PATH_NOT_EXPORTED' },
  );
  const direct = await import(pathToFileURL(join(packageRoot, 'private.mjs')));
  assert.equal(direct.hidden, 2);

  // exports 约束包说明符解析，不是 OS 权限；知道并可访问真实 file URL 的代码仍能加载文件。
});
