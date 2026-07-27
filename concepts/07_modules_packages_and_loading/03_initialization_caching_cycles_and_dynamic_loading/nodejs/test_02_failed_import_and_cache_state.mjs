// 失败初始化、缓存状态与重试。
// 共同问题：初始化失败的模块是否留在缓存；同一键再次加载是否重新执行；
// 循环依赖为何可能只看到部分初始化状态。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/nodejs/language/test_029_esm_live_bindings_namespace_dynamic_import_and_metadata.mjs

import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

test('失败的 ESM module record 按同一 URL 缓存 rejection', async (t) => {
  const counterKey = `__polyglot_failed_module_${process.pid}_${Date.now()}`;
  t.after(() => {
    delete globalThis[counterKey];
  });
  const source = [
    `globalThis[${JSON.stringify(counterKey)}] = (globalThis[${JSON.stringify(counterKey)}] ?? 0) + 1;`,
    "throw new Error('initialization failed');",
  ].join('\n');
  const url = `data:text/javascript,${encodeURIComponent(source)}#failed`;

  await assert.rejects(import(url), /initialization failed/);
  await assert.rejects(import(url), /initialization failed/);

  assert.equal(globalThis[counterKey], 1);

  // 与 Python 失败后删除 sys.modules 项不同，ESM module map 保留同一 URL 的失败记录；
  // 重新 import 返回 rejection 而不重新执行。改变 URL 才是不同缓存键。
});

test('循环依赖可观察尚未赋值的 var live binding', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-cycle-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const left = join(root, 'left.mjs');
  const right = join(root, 'right.mjs');
  await writeFile(
    left,
    "import { seen } from './right.mjs';\nexport var value = 'left';\nexport const observed = seen;\n",
  );
  await writeFile(
    right,
    "import { value } from './left.mjs';\nexport const seen = value;\n",
  );

  const namespace = await import(pathToFileURL(left));

  assert.equal(namespace.value, 'left');
  assert.equal(namespace.observed, undefined);

  // var binding 在循环实例化时先初始化为 undefined；改用 const 并在初始化前读取会触发
  // TDZ ReferenceError。应通过函数延迟读取，而不是依赖部分初始化值。
});
