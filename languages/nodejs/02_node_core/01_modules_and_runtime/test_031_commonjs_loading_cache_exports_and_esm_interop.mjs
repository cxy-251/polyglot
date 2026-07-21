// polyglot-covers:
// - nodejs.core.commonjs-create-require
// - nodejs.core.commonjs-module-exports-alias
// - nodejs.core.commonjs-cache-and-invalidation
// - nodejs.core.commonjs-filename-dirname-and-main
// - nodejs.core.commonjs-require-esm
// - nodejs.core.esm-import-commonjs
// - nodejs.core.commonjs-resolution

import assert from 'node:assert/strict';
import test from 'node:test';

import { createRequire } from 'node:module';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const fixturesDirectory = new URL('./fixtures/', import.meta.url);
const counterPath = require.resolve('./fixtures/commonjs_counter.cjs');

test.beforeEach(() => {
  delete require.cache[counterPath];
});

test('createRequire 让 ESM 使用以当前模块为基准的 CommonJS require', () => {
  const counter = require('./fixtures/commonjs_counter.cjs');

  assert.equal(typeof require, 'function');
  assert.equal(counter.read(), 0);
  assert.equal(counter.increment(), 1);
  assert.equal(require.resolve('./fixtures/commonjs_counter.cjs'), fileURLToPath(
    new URL('commonjs_counter.cjs', fixturesDirectory),
  ));
});

test('CommonJS 按解析后的文件名缓存 module.exports 对象', () => {
  const resolved = require.resolve('./fixtures/commonjs_counter.cjs');
  const first = require(resolved);
  const second = require(resolved);

  assert.equal(first, second);
  assert.equal(first.read(), 0);
  first.increment();
  assert.equal(second.read(), 1);
  assert.equal(require.cache[resolved].exports, first);

  delete require.cache[resolved];
  const fresh = require(resolved);
  assert.notEqual(fresh, first);
  assert.equal(fresh.read(), 0);

  // 删除 cache 只影响以后 require；已经持有的旧导出及其状态不会自动失效。
  assert.equal(first.read(), 1);
});

test('exports 初始只是 module.exports 的别名，重绑定不会改变实际导出', () => {
  const value = require('./fixtures/exports_alias.cjs');

  assert.deepEqual(value, {
    final: 'module.exports remains authoritative',
    visible: 'attached through initial alias',
  });
  assert.equal(value.lost, undefined);
  assert.equal(value.lostAgain, undefined);
});

test('CommonJS wrapper 提供 __filename、__dirname、module 和 require', () => {
  const metadata = require('./fixtures/commonjs_metadata.cjs');

  assert.equal(metadata.filename.endsWith('/fixtures/commonjs_metadata.cjs'), true);
  assert.equal(metadata.dirname, dirname(metadata.filename));
  assert.equal(metadata.isMain, false);

  // ESM 没有这些词法变量，使用 import.meta.url 和 URL/fileURLToPath 显式转换。
  assert.equal(typeof import.meta.url, 'string');
  assert.equal(typeof globalThis.__filename, 'undefined');
});

test('Node 24 可同步 require 不含 top-level await 的 ESM', () => {
  const namespace = require('./fixtures/synchronous_esm.mjs');

  assert.equal(Object.prototype.toString.call(namespace), '[object Module]');
  assert.equal(namespace.answer, 42);
  assert.equal(namespace.default, 'esm default');
  assert.equal(namespace.__esModule, true);
});

test('require 不能同步加载包含 top-level await 的 ESM 图', () => {
  assert.throws(
    () => require('./fixtures/asynchronous_esm.mjs'),
    (error) => error.code === 'ERR_REQUIRE_ASYNC_MODULE',
  );

  // dynamic import 返回 Promise，能够等待异步模块完成。
});

test('ESM import CommonJS 时 default 对应 module.exports', async () => {
  const namespace = await import('./fixtures/commonjs_counter.cjs');
  const required = require('./fixtures/commonjs_counter.cjs');

  assert.equal(namespace.default, required);
  assert.equal(namespace['module.exports'], required);
  assert.equal(namespace.default.read(), 0);

  namespace.default.increment();
  assert.equal(required.read(), 1);
});

test('require.resolve 只解析路径，不执行目标模块', () => {
  const resolved = require.resolve('./fixtures/commonjs_counter.cjs');
  delete require.cache[resolved];

  assert.equal(require.resolve('./fixtures/commonjs_counter.cjs'), resolved);
  assert.equal(require.cache[resolved], undefined);

  const paths = require.resolve.paths('hypothetical-package');
  assert.ok(paths.some((path) => path.endsWith('/node_modules')));
});
