// polyglot-covers:
// - nodejs.core.packages-type-field
// - nodejs.core.packages-main-and-exports
// - nodejs.core.packages-conditional-exports
// - nodejs.core.packages-subpath-exports
// - nodejs.core.packages-imports
// - nodejs.core.packages-self-reference
// - nodejs.core.package-encapsulation

import assert from 'node:assert/strict';
import test from 'node:test';

import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const createWorkspace = async (t) => {
  const root = await mkdtemp('/tmp/polyglot-nodejs-packages-');
  t.after(() => rm(root, { force: true, recursive: true }));
  return root;
};

const writeJson = (path, value) => writeFile(path, `${JSON.stringify(value, null, 2)}\n`);

test('type 字段决定包范围内 .js 按 ESM 或 CommonJS 解释', async (t) => {
  const root = await createWorkspace(t);
  const esmDirectory = join(root, 'esm');
  const commonjsDirectory = join(root, 'commonjs');
  await mkdir(esmDirectory);
  await mkdir(commonjsDirectory);

  await writeJson(join(esmDirectory, 'package.json'), { type: 'module' });
  await writeFile(join(esmDirectory, 'entry.js'), 'export default "esm";\n');
  await writeJson(join(commonjsDirectory, 'package.json'), { type: 'commonjs' });
  await writeFile(join(commonjsDirectory, 'entry.js'), 'module.exports = "commonjs";\n');

  const esm = await import(pathToFileURL(join(esmDirectory, 'entry.js')));
  const commonjs = await import(pathToFileURL(join(commonjsDirectory, 'entry.js')));

  assert.equal(esm.default, 'esm');
  assert.equal(commonjs.default, 'commonjs');
});

test('.mjs 与 .cjs 显式覆盖 package type', async (t) => {
  const root = await createWorkspace(t);
  await writeJson(join(root, 'package.json'), { type: 'module' });
  await writeFile(join(root, 'explicit.cjs'), 'module.exports = { kind: "cjs" };\n');
  await writeFile(join(root, 'explicit.mjs'), 'export const kind = "esm";\n');

  assert.equal((await import(pathToFileURL(join(root, 'explicit.cjs')))).default.kind, 'cjs');
  assert.equal((await import(pathToFileURL(join(root, 'explicit.mjs')))).kind, 'esm');
});

test('exports 可为 import 与 require 选择不同入口', async (t) => {
  const root = await createWorkspace(t);
  const appDirectory = join(root, 'app');
  const packageDirectory = join(appDirectory, 'node_modules', 'demo-package');
  await mkdir(packageDirectory, { recursive: true });

  await writeJson(join(packageDirectory, 'package.json'), {
    name: 'demo-package',
    exports: {
      '.': {
        import: './import.mjs',
        require: './require.cjs',
      },
    },
  });
  await writeFile(join(packageDirectory, 'import.mjs'), 'export default "import branch";\n');
  await writeFile(join(packageDirectory, 'require.cjs'), 'module.exports = "require branch";\n');
  await writeFile(
    join(appDirectory, 'entry.mjs'),
    'import value from "demo-package"; export default value;\n',
  );

  const imported = await import(pathToFileURL(join(appDirectory, 'entry.mjs')));
  const require = createRequire(join(appDirectory, 'entry.cjs'));

  assert.equal(imported.default, 'import branch');
  assert.equal(require('demo-package'), 'require branch');
});

test('exports 只公开声明的子路径并形成包封装边界', async (t) => {
  const root = await createWorkspace(t);
  const appDirectory = join(root, 'app');
  const packageDirectory = join(appDirectory, 'node_modules', 'encapsulated');
  await mkdir(packageDirectory, { recursive: true });

  await writeJson(join(packageDirectory, 'package.json'), {
    name: 'encapsulated',
    exports: {
      '.': './index.cjs',
      './feature': './feature.cjs',
    },
  });
  await writeFile(join(packageDirectory, 'index.cjs'), 'module.exports = "root";\n');
  await writeFile(join(packageDirectory, 'feature.cjs'), 'module.exports = "feature";\n');
  await writeFile(join(packageDirectory, 'private.cjs'), 'module.exports = "private";\n');

  const require = createRequire(join(appDirectory, 'entry.cjs'));
  assert.equal(require('encapsulated'), 'root');
  assert.equal(require('encapsulated/feature'), 'feature');
  assert.throws(
    () => require('encapsulated/private.cjs'),
    (error) => error.code === 'ERR_PACKAGE_PATH_NOT_EXPORTED',
  );

  // exports 不是文件系统安全边界；知道绝对路径的代码仍可直接读取文件。
});

test('imports 为包内部说明符提供以 # 开头的私有映射', async (t) => {
  const root = await createWorkspace(t);
  await writeJson(join(root, 'package.json'), {
    imports: {
      '#config': './config.mjs',
    },
    type: 'module',
  });
  await writeFile(join(root, 'config.mjs'), 'export const mode = "test";\n');
  await writeFile(
    join(root, 'entry.mjs'),
    'import { mode } from "#config"; export default mode;\n',
  );

  assert.equal((await import(pathToFileURL(join(root, 'entry.mjs')))).default, 'test');
});

test('包名 self-reference 也经过 exports 解析', async (t) => {
  const root = await createWorkspace(t);
  await writeJson(join(root, 'package.json'), {
    exports: {
      '.': './index.mjs',
      './feature': './feature.mjs',
    },
    name: 'self-demo',
    type: 'module',
  });
  await writeFile(join(root, 'feature.mjs'), 'export const value = 42;\n');
  await writeFile(
    join(root, 'index.mjs'),
    'export { value } from "self-demo/feature";\n',
  );

  assert.equal((await import(pathToFileURL(join(root, 'index.mjs')))).value, 42);
});

test('main 是旧式回退，exports 存在时拥有更高优先级', async (t) => {
  const root = await createWorkspace(t);
  const appDirectory = join(root, 'app');
  const packageDirectory = join(appDirectory, 'node_modules', 'entry-demo');
  await mkdir(packageDirectory, { recursive: true });

  await writeJson(join(packageDirectory, 'package.json'), {
    exports: './modern.cjs',
    main: './legacy.cjs',
    name: 'entry-demo',
  });
  await writeFile(join(packageDirectory, 'legacy.cjs'), 'module.exports = "legacy";\n');
  await writeFile(join(packageDirectory, 'modern.cjs'), 'module.exports = "modern";\n');

  const require = createRequire(join(appDirectory, 'entry.cjs'));
  assert.equal(require('entry-demo'), 'modern');
});
