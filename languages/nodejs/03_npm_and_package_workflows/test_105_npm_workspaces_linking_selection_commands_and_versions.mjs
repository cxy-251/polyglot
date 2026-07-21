// polyglot-covers:
// - nodejs.npm.workspaces-manifest-globs-install-auto-links-and-lock-entries
// - nodejs.npm.workspace-to-workspace-dependency-standard-semver-range
// - nodejs.npm.workspace-node-resolution-from-root-link
// - nodejs.npm.run-workspaces-declaration-order-name-path-directory-and-if-present
// - nodejs.npm.workspace-implicit-selection-from-child-directory-and-root-prefix
// - nodejs.npm.pkg-get-set-delete-across-workspaces-result-shape
// - nodejs.npm.init-workspace-directory-manifest-and-root-registration
// - nodejs.npm.version-selected-workspace-lock-update-and-root-exclusion
// - nodejs.npm.workspace-duplicate-name-install-error

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  lstat,
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

function isolatedNpmEnvironment(root, overrides = {}) {
  return {
    ...process.env,
    HOME: join(root, '.home'),
    NO_COLOR: '1',
    npm_config_audit: 'false',
    npm_config_cache: join(root, '.npm-cache'),
    npm_config_color: 'false',
    npm_config_fund: 'false',
    npm_config_offline: 'true',
    npm_config_update_notifier: 'false',
    npm_config_userconfig: join(root, '.npmrc-user'),
    ...overrides,
  };
}

async function runNpm(root, argumentsList, options = {}) {
  const cwd = options.cwd ?? root;
  try {
    const result = await execFileAsync('npm', argumentsList, {
      cwd,
      encoding: 'utf8',
      env: isolatedNpmEnvironment(root, options.env),
    });
    return { code: 0, ...result };
  } catch (error) {
    return {
      code: error.code,
      signal: error.signal,
      stdout: error.stdout,
      stderr: error.stderr,
    };
  }
}

async function createRoot(manifest = {}) {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-npm-workspaces-'));
  await mkdir(join(root, '.home'));
  await writeFile(join(root, 'package.json'), JSON.stringify({
    name: 'workspace-root',
    version: '1.0.0',
    private: true,
    ...manifest,
  }, null, 2));
  return root;
}

async function writeWorkspace(root, directory, manifest, source = undefined) {
  const path = join(root, directory);
  await mkdir(path, { recursive: true });
  await writeFile(join(path, 'package.json'), JSON.stringify(manifest, null, 2));
  if (source !== undefined) {
    await writeFile(join(path, 'index.js'), source);
  }
  return path;
}

async function readJSON(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

test('npm install 自动链接 workspace，并把链接目标写入根 lock', async () => {
  const root = await createRoot({ workspaces: ['packages/*'] });
  const core = await writeWorkspace(root, 'packages/core', {
    name: '@lesson/core',
    version: '1.0.0',
    main: 'index.js',
  }, 'module.exports = { value: 42 };');
  const app = await writeWorkspace(root, 'packages/app', {
    name: '@lesson/app',
    version: '1.0.0',
    main: 'index.js',
    dependencies: {
      '@lesson/core': '^1.0.0',
    },
  }, 'module.exports = require("@lesson/core").value;');
  try {
    const installed = await runNpm(root, ['install', '--ignore-scripts']);
    assert.equal(installed.code, 0);
    const coreLink = join(root, 'node_modules', '@lesson', 'core');
    const appLink = join(root, 'node_modules', '@lesson', 'app');
    assert.equal((await lstat(coreLink)).isSymbolicLink(), true);
    assert.equal((await lstat(appLink)).isSymbolicLink(), true);
    assert.equal(await realpath(coreLink), core);
    assert.equal(await realpath(appLink), app);

    const loaded = await execFileAsync(process.execPath, [
      '--input-type=commonjs',
      '--eval',
      'process.stdout.write(String(require("@lesson/app")));',
    ], { cwd: root, encoding: 'utf8' });
    assert.equal(loaded.stdout, '42');

    const lock = await readJSON(join(root, 'package-lock.json'));
    assert.equal(lock.packages['node_modules/@lesson/core'].link, true);
    assert.equal(lock.packages['node_modules/@lesson/app'].link, true);
    assert.equal(lock.packages['packages/core'].version, '1.0.0');
    assert.equal(
      lock.packages['packages/app'].dependencies['@lesson/core'],
      '^1.0.0',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test(
  '给 workspace 安装另一 workspace 时保存普通 semver，而不是私有协议',
  async () => {
  const root = await createRoot({
    workspaces: ['packages/core', 'packages/app'],
  });
  await writeWorkspace(root, 'packages/core', {
    name: '@lesson/core',
    version: '2.3.4',
    main: 'index.js',
  }, 'module.exports = 234;');
  const app = await writeWorkspace(root, 'packages/app', {
    name: '@lesson/app',
    version: '1.0.0',
    private: true,
  });
  try {
    const installed = await runNpm(root, [
      'install',
      '@lesson/core',
      '--workspace=@lesson/app',
    ]);
    assert.equal(installed.code, 0);
    const appManifest = await readJSON(join(app, 'package.json'));
    assert.equal(appManifest.dependencies['@lesson/core'], '^2.3.4');
    assert.equal(
      (await lstat(join(root, 'node_modules', '@lesson', 'core')))
        .isSymbolicLink(),
      true,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // 标准 semver 让单个 workspace 发布后仍可被普通 npm 消费；
  // 当前仓库内满足范围时，安装器才选择本地 workspace 链接。
  },
);

test('--workspaces 按清单声明顺序运行，--if-present 跳过缺失脚本', async () => {
  const root = await createRoot({
    workspaces: ['packages/b', 'packages/a', 'packages/c'],
  });
  const log = join(root, 'order.log');
  await writeFile(join(root, 'record.mjs'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, JSON.stringify({
      name: process.env.npm_package_name,
      cwd: process.cwd(),
      event: process.env.npm_lifecycle_event,
    }) + '\\n');
  `);
  for (const name of ['b', 'a']) {
    await writeWorkspace(root, `packages/${name}`, {
      name: `@lesson/${name}`,
      version: '1.0.0',
      scripts: { inspect: 'node ../../record.mjs' },
    });
  }
  await writeWorkspace(root, 'packages/c', {
    name: '@lesson/c',
    version: '1.0.0',
  });
  try {
    const all = await runNpm(root, [
      'run',
      '--silent',
      'inspect',
      '--workspaces',
      '--if-present',
    ], { env: { LOG_FILE: log } });
    assert.equal(all.code, 0);
    const records = (await readFile(log, 'utf8'))
      .trim()
      .split('\n')
      .map((line) => JSON.parse(line));
    assert.deepEqual(records.map(({ name }) => name), [
      '@lesson/b',
      '@lesson/a',
    ]);
    assert.deepEqual(records.map(({ cwd }) => cwd), [
      join(root, 'packages', 'b'),
      join(root, 'packages', 'a'),
    ]);
    assert.ok(records.every(({ event }) => event === 'inspect'));

    await rm(log, { force: true });
    const selected = await runNpm(root, [
      'run',
      '--silent',
      'inspect',
      '--workspace=@lesson/a',
      '--workspace=packages/b',
    ], { env: { LOG_FILE: log } });
    assert.equal(selected.code, 0);
    const names = (await readFile(log, 'utf8'))
      .trim()
      .split('\n')
      .map((line) => JSON.parse(line).name);
    assert.deepEqual(names, ['@lesson/a', '@lesson/b']);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // 多个 --workspace 按命令行选择顺序执行；--workspaces 才按根清单顺序执行。
});

test(
  '从 workspace 子目录运行 npm 会隐式选中它，并仍以根项目为 prefix',
  async () => {
  const root = await createRoot({ workspaces: ['packages/*'] });
  const workspace = await writeWorkspace(root, 'packages/only', {
    name: '@lesson/only',
    version: '1.0.0',
    scripts: {
      inspect: 'node -e "process.stdout.write(process.cwd())"',
    },
  });
  try {
    const run = await runNpm(root, ['run', '--silent', 'inspect'], {
      cwd: workspace,
    });
    assert.equal(run.code, 0);
    assert.equal(run.stdout, workspace);

    const prefix = await runNpm(root, ['prefix'], { cwd: workspace });
    assert.equal(prefix.code, 0);
    assert.equal(prefix.stdout.trim(), root);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  },
);

test('npm pkg 可批量查询、设置和删除 workspace 字段', async () => {
  const root = await createRoot({
    workspaces: ['packages/alpha', 'packages/beta'],
  });
  const alpha = await writeWorkspace(root, 'packages/alpha', {
    name: '@lesson/alpha',
    version: '1.0.0',
  });
  const beta = await writeWorkspace(root, 'packages/beta', {
    name: '@lesson/beta',
    version: '2.0.0',
  });
  try {
    const queried = await runNpm(root, [
      'pkg',
      'get',
      'name',
      'version',
      '--workspaces',
    ]);
    assert.equal(queried.code, 0);
    assert.deepEqual(JSON.parse(queried.stdout), {
      '@lesson/alpha': { name: '@lesson/alpha', version: '1.0.0' },
      '@lesson/beta': { name: '@lesson/beta', version: '2.0.0' },
    });

    const set = await runNpm(root, [
      'pkg',
      'set',
      'funding=https://example.test/workspaces',
      '--workspaces',
    ]);
    assert.equal(set.code, 0);
    assert.equal(
      (await readJSON(join(alpha, 'package.json'))).funding,
      'https://example.test/workspaces',
    );
    assert.equal(
      (await readJSON(join(beta, 'package.json'))).funding,
      'https://example.test/workspaces',
    );
    assert.equal(
      (await readJSON(join(root, 'package.json'))).funding,
      undefined,
    );

    const deleted = await runNpm(root, [
      'pkg',
      'delete',
      'funding',
      '--workspace=@lesson/alpha',
    ]);
    assert.equal(deleted.code, 0);
    assert.equal((await readJSON(join(alpha, 'package.json'))).funding, undefined);
    assert.equal(
      (await readJSON(join(beta, 'package.json'))).funding,
      'https://example.test/workspaces',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('npm init -w 创建清单并把新目录登记进根 workspaces', async () => {
  const root = await createRoot();
  try {
    const initialized = await runNpm(root, [
      'init',
      '--yes',
      '--workspace=packages/new-tool',
    ]);
    assert.equal(initialized.code, 0);
    const rootManifest = await readJSON(join(root, 'package.json'));
    assert.deepEqual(rootManifest.workspaces, ['packages/new-tool']);
    const child = await readJSON(join(
      root,
      'packages',
      'new-tool',
      'package.json',
    ));
    assert.equal(child.name, 'new-tool');
    assert.equal(child.version, '1.0.0');
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('npm version 可只升级选定 workspace，并同步根 lock 的目标描述', async () => {
  const root = await createRoot({
    workspaces: ['packages/core', 'packages/app'],
  });
  const core = await writeWorkspace(root, 'packages/core', {
    name: '@lesson/core',
    version: '1.0.0',
  });
  const app = await writeWorkspace(root, 'packages/app', {
    name: '@lesson/app',
    version: '1.0.0',
  });
  try {
    assert.equal((await runNpm(root, ['install'])).code, 0);
    const versioned = await runNpm(root, [
      'version',
      'minor',
      '--workspace=@lesson/core',
      '--no-git-tag-version',
    ]);
    assert.equal(versioned.code, 0);
    assert.match(versioned.stdout, /@lesson\/core/);
    assert.match(versioned.stdout, /v1\.1\.0/);
    assert.equal((await readJSON(join(core, 'package.json'))).version, '1.1.0');
    assert.equal((await readJSON(join(app, 'package.json'))).version, '1.0.0');
    assert.equal((await readJSON(join(root, 'package.json'))).version, '1.0.0');
    assert.equal(
      (await readJSON(join(root, 'package-lock.json')))
        .packages['packages/core'].version,
      '1.1.0',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // 只有显式 --include-workspace-root 才把根包也纳入批量 workspace 操作。
});

test(
  '两个 workspace 声明同名包会让安装失败，目录名不能充当身份',
  async () => {
  const root = await createRoot({ workspaces: ['packages/*'] });
  await writeWorkspace(root, 'packages/first', {
    name: '@lesson/duplicate',
    version: '1.0.0',
  });
  await writeWorkspace(root, 'packages/second', {
    name: '@lesson/duplicate',
    version: '2.0.0',
  });
  try {
    const result = await runNpm(root, ['install']);
    assert.notEqual(result.code, 0);
    assert.match(result.stderr, /EDUPLICATEWORKSPACE/);
    assert.match(result.stderr, /must not have multiple workspaces with the same name/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  },
);
