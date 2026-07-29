// polyglot-covers:
// - nodejs.core.module-builtin-modules-and-is-builtin
// - nodejs.core.module-create-require-and-resolve
// - nodejs.core.module-find-package-json
// - nodejs.core.module-sync-builtin-esm-exports
// - nodejs.core.module-enable-compile-cache
// - nodejs.core.module-cache-boundaries

import assert from 'node:assert/strict';
import test from 'node:test';

import * as fsNamespace from 'node:fs';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import {
  builtinModules,
  constants,
  createRequire,
  enableCompileCache,
  findPackageJSON,
  flushCompileCache,
  isBuiltin,
  syncBuiltinESMExports,
} from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

test('builtinModules 与 isBuiltin 识别核心模块说明符', () => {
  assert.ok(builtinModules.includes('fs'));
  assert.ok(builtinModules.includes('node:test'));
  assert.equal(isBuiltin('fs'), true);
  assert.equal(isBuiltin('node:fs'), true);
  assert.equal(isBuiltin('test'), false);
  assert.equal(isBuiltin('definitely-not-a-module'), false);

  // builtinModules 的条目并非全部统一带 node: 前缀，判定时优先使用 isBuiltin。
});

test('createRequire 的解析基准来自传入文件 URL 或绝对路径', () => {
  const require = createRequire(import.meta.url);
  const currentDirectory = dirname(fileURLToPath(import.meta.url));
  const resolved = require.resolve('./fixtures/commonjs_counter.cjs');

  assert.equal(dirname(resolved), `${currentDirectory}/fixtures`);
  assert.equal(require('node:path').basename(resolved), 'commonjs_counter.cjs');
  assert.equal(require.resolve('node:fs'), 'node:fs');
});

test('findPackageJSON 从显式模块位置向上查找最近 package.json', (t) => {
  const directory = mkdtempSync('/tmp/polyglot-nodejs-package-json-');
  t.after(() => rmSync(directory, { force: true, recursive: true }));
  writeFileSync(join(directory, 'package.json'), '{"name":"fixture"}');
  writeFileSync(join(directory, 'entry.mjs'), '');
  const packagePath = findPackageJSON(
    '.',
    pathToFileURL(join(directory, 'entry.mjs')),
  );

  assert.equal(packagePath, join(directory, 'package.json'));
});

test('CommonJS 修改 builtin 导出后可显式同步到 ESM named exports', () => {
  const require = createRequire(import.meta.url);
  const commonjsFs = require('node:fs');
  const original = commonjsFs.readFileSync;
  const replacement = () => Buffer.from('replacement');

  try {
    commonjsFs.readFileSync = replacement;
    assert.notEqual(fsNamespace.readFileSync, replacement);

    syncBuiltinESMExports();
    assert.equal(fsNamespace.readFileSync, replacement);
  } finally {
    commonjsFs.readFileSync = original;
    syncBuiltinESMExports();
  }

  assert.equal(fsNamespace.readFileSync, original);
});

test('compile cache API 返回状态并可显式 flush 到磁盘', (t) => {
  const directory = mkdtempSync('/tmp/polyglot-nodejs-compile-cache-');
  t.after(() => {
    flushCompileCache();
    rmSync(directory, { force: true, recursive: true });
  });
  const result = enableCompileCache(directory);

  assert.ok(Object.values(constants.compileCacheStatus).includes(result.status));
  assert.ok([
    constants.compileCacheStatus.ALREADY_ENABLED,
    constants.compileCacheStatus.ENABLED,
  ].includes(result.status));
  assert.equal(result.directory, directory);
  assert.equal(typeof flushCompileCache(), 'undefined');

  // compile cache 只缓存编译产物，不替代 CommonJS/ESM 的模块实例缓存。
});
