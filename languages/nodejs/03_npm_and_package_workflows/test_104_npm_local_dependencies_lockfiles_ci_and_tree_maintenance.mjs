// polyglot-covers:
// - nodejs.npm.install-local-folder-save-prod-dev-optional-and-no-save
// - nodejs.npm.install-outside-folder-link-versus-install-links-copy
// - nodejs.npm.install-peer-dependency-resolution-conflict-and-legacy-peer-deps
// - nodejs.npm.package-lock-v3-root-packages-resolved-integrity-and-hidden-lock
// - nodejs.npm.install-package-lock-only-without-node-modules
// - nodejs.npm.ci-required-lock-clean-tree-frozen-manifest-and-reproducible-tarball
// - nodejs.npm.ci-omit-dev-and-optional-platform-filtering
// - nodejs.npm.ls-json-problems-extraneous-and-prune-dry-run
// - nodejs.npm.uninstall-manifest-lock-and-tree-update
// - nodejs.npm.shrinkwrap-precedence-and-publishable-lock-boundary

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  access,
  cp,
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

async function runNpm(root, cwd, argumentsList, options = {}) {
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

async function createRoot() {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-npm-dependencies-'));
  await mkdir(join(root, '.home'));
  return root;
}

async function writePackage(directory, manifest, source = undefined) {
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'package.json'),
    JSON.stringify(manifest, null, 2),
  );
  if (source !== undefined) {
    await writeFile(join(directory, 'index.js'), source);
  }
}

async function readJSON(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

test(
  '本地包可分别保存为生产、开发、可选依赖，--no-save 只改安装树',
  async () => {
  const root = await createRoot();
  const project = join(root, 'application');
  const vendor = join(project, 'vendor');
  await writePackage(project, {
    name: 'dependency-sections-lesson',
    version: '1.0.0',
    private: true,
  });
  for (const [folder, name] of [
    ['production', 'production-tool'],
    ['development', 'development-tool'],
    ['optional', 'optional-tool'],
    ['transient', 'transient-tool'],
  ]) {
    await writePackage(join(vendor, folder), {
      name,
      version: '1.0.0',
      main: 'index.js',
    }, `module.exports = ${JSON.stringify(name)};`);
  }

  try {
    assert.equal((await runNpm(root, project, [
      'install',
      './vendor/production',
      '--save-prod',
    ])).code, 0);
    assert.equal((await runNpm(root, project, [
      'install',
      './vendor/development',
      '--save-dev',
    ])).code, 0);
    assert.equal((await runNpm(root, project, [
      'install',
      './vendor/optional',
      '--save-optional',
    ])).code, 0);
    assert.equal((await runNpm(root, project, [
      'install',
      './vendor/transient',
      '--no-save',
    ])).code, 0);

    const manifest = await readJSON(join(project, 'package.json'));
    assert.equal(manifest.dependencies['production-tool'], 'file:vendor/production');
    assert.equal(
      manifest.devDependencies['development-tool'],
      'file:vendor/development',
    );
    assert.equal(
      manifest.optionalDependencies['optional-tool'],
      'file:vendor/optional',
    );
    assert.equal(manifest.dependencies?.['transient-tool'], undefined);
    assert.equal(manifest.devDependencies?.['transient-tool'], undefined);
    assert.equal(manifest.optionalDependencies?.['transient-tool'], undefined);
    for (const name of [
      'production-tool',
      'development-tool',
      'optional-tool',
      'transient-tool',
    ]) {
      assert.equal(await pathExists(join(project, 'node_modules', name)), true);
    }
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // optionalDependencies 会覆盖同名 dependencies；失败时可跳过，
    // 业务代码仍要处理缺失。
  },
);

test(
  '项目外文件夹默认链接开发目录，--install-links 改为打包后的副本',
  async () => {
  const root = await createRoot();
  const dependency = join(root, 'shared-library');
  const linkedProject = join(root, 'linked-app');
  const copiedProject = join(root, 'copied-app');
  await writePackage(dependency, {
    name: 'shared-library',
    version: '1.0.0',
    main: 'index.js',
  }, 'module.exports = "shared";');
  await writePackage(linkedProject, {
    name: 'linked-app',
    version: '1.0.0',
    private: true,
  });
  await writePackage(copiedProject, {
    name: 'copied-app',
    version: '1.0.0',
    private: true,
  });
  try {
    const linked = await runNpm(root, linkedProject, [
      'install',
      '../shared-library',
    ]);
    assert.equal(linked.code, 0);
    const linkedPath = join(linkedProject, 'node_modules', 'shared-library');
    assert.equal((await lstat(linkedPath)).isSymbolicLink(), true);
    assert.equal(await realpath(linkedPath), dependency);

    const copied = await runNpm(root, copiedProject, [
      'install',
      '../shared-library',
      '--install-links',
    ]);
    assert.equal(copied.code, 0);
    const copiedPath = join(copiedProject, 'node_modules', 'shared-library');
    assert.equal((await lstat(copiedPath)).isDirectory(), true);
    assert.equal((await lstat(copiedPath)).isSymbolicLink(), false);
    await writeFile(join(dependency, 'index.js'), 'module.exports = "changed";');
    assert.equal(
      await readFile(join(copiedPath, 'index.js'), 'utf8'),
      'module.exports = "shared";',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // 链接适合联调但内容会随源目录变化；
    // install-links 更接近 registry tarball 安装。
  },
);

test(
  'peerDependencies 表达宿主契约，冲突默认失败而 legacy 模式忽略约束',
  async () => {
  const root = await createRoot();
  const project = join(root, 'peer-app');
  const host = join(project, 'vendor', 'host');
  const plugin = join(project, 'vendor', 'plugin');
  await writePackage(project, {
    name: 'peer-app',
    version: '1.0.0',
    private: true,
    dependencies: {
      'host-library': 'file:vendor/host',
      'host-plugin': 'file:vendor/plugin',
    },
  });
  await writePackage(host, {
    name: 'host-library',
    version: '2.0.0',
    main: 'index.js',
  }, 'module.exports = 2;');
  await writePackage(plugin, {
    name: 'host-plugin',
    version: '1.0.0',
    main: 'index.js',
    peerDependencies: {
      'host-library': '^1.0.0',
    },
  }, 'module.exports = require("host-library");');
  try {
    const conflict = await runNpm(root, project, ['install']);
    assert.equal(conflict.code, 1);
    assert.match(conflict.stderr, /ERESOLVE/);
    assert.match(conflict.stderr, /peer host-library@"\^1\.0\.0"/);

    const legacy = await runNpm(root, project, [
      'install',
      '--legacy-peer-deps',
    ]);
    assert.equal(legacy.code, 0);
    assert.equal(
      (await readJSON(join(
        project,
        'node_modules',
        'host-library',
        'package.json',
      ))).version,
      '2.0.0',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // legacy-peer-deps 是兼容逃生口，
    // 不会修复插件与宿主 API 真的不兼容这一事实。
  },
);

test('package-lock v3 固定 tarball 完整性，npm ci 清空旧树并冻结清单', async () => {
  const root = await createRoot();
  const project = join(root, 'locked-app');
  const source = join(root, 'locked-source');
  const vendor = join(project, 'vendor');
  await writePackage(source, {
    name: 'locked-library',
    version: '1.0.0',
    main: 'index.js',
    files: ['index.js'],
  }, 'module.exports = "locked-original";');
  await writePackage(project, {
    name: 'locked-app',
    version: '1.0.0',
    private: true,
  });
  await mkdir(vendor, { recursive: true });
  try {
    const packed = await runNpm(root, source, [
      'pack',
      '--json',
      '--pack-destination',
      vendor,
    ]);
    assert.equal(packed.code, 0);
    const tarballName = JSON.parse(packed.stdout)[0].filename;
    const relativeTarball = `vendor/${tarballName}`;
    const installed = await runNpm(root, project, [
      'install',
      `./${relativeTarball}`,
      '--save-exact',
    ]);
    assert.equal(installed.code, 0);

    const lockPath = join(project, 'package-lock.json');
    const lockText = await readFile(lockPath, 'utf8');
    const lock = JSON.parse(lockText);
    assert.equal(lock.lockfileVersion, 3);
    assert.equal(lock.packages[''].name, 'locked-app');
    assert.equal(
      lock.packages[''].dependencies['locked-library'],
      `file:${relativeTarball}`,
    );
    const descriptor = lock.packages['node_modules/locked-library'];
    assert.equal(descriptor.version, '1.0.0');
    assert.equal(descriptor.resolved, `file:${relativeTarball}`);
    assert.match(descriptor.integrity, /^sha512-/);
    assert.equal(
      (await readJSON(join(project, 'node_modules', '.package-lock.json')))
        .lockfileVersion,
      3,
    );

    await writeFile(
      join(project, 'node_modules', 'locked-library', 'index.js'),
      'module.exports = "mutated";',
    );
    await writePackage(join(project, 'node_modules', 'extraneous'), {
      name: 'extraneous',
      version: '1.0.0',
    });
    const clean = await runNpm(root, project, ['ci', '--ignore-scripts']);
    assert.equal(clean.code, 0);
    assert.equal(
      await readFile(
        join(project, 'node_modules', 'locked-library', 'index.js'),
        'utf8',
      ),
      'module.exports = "locked-original";',
    );
    assert.equal(
      await pathExists(join(project, 'node_modules', 'extraneous')),
      false,
    );
    assert.equal(await readFile(lockPath, 'utf8'), lockText);

    const invalidLock = JSON.parse(lockText);
    delete invalidLock.packages['node_modules/locked-library'];
    const invalidLockText = `${JSON.stringify(invalidLock, null, 2)}\n`;
    await writeFile(lockPath, invalidLockText);
    const mismatch = await runNpm(root, project, ['ci', '--ignore-scripts']);
    assert.notEqual(mismatch.code, 0);
    assert.match(mismatch.stderr, /npm ci.*package\.json.*package-lock/i);
    assert.match(mismatch.stderr, /Missing: locked-library.*from lock file/);
    assert.equal(await readFile(lockPath, 'utf8'), invalidLockText);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // package-lock 应提交，node_modules 与隐藏锁不提交；只有 tarball/registry 依赖
  // 具备 integrity，file 目录依赖仍会读取当前工作树，并非不可变制品。
});

test(
  '--package-lock-only 不建安装树；ci --omit=dev 仍在锁中保留开发依赖',
  async () => {
  const root = await createRoot();
  const project = join(root, 'omit-app');
  const production = join(project, 'vendor', 'production');
  const development = join(project, 'vendor', 'development');
  const optional = join(project, 'vendor', 'darwin-only');
  await writePackage(project, {
    name: 'omit-app',
    version: '1.0.0',
    private: true,
    dependencies: {
      'production-library': 'file:vendor/production',
    },
    devDependencies: {
      'development-library': 'file:vendor/development',
    },
    optionalDependencies: {
      'darwin-only-library': 'file:vendor/darwin-only',
    },
  });
  await writePackage(production, {
    name: 'production-library',
    version: '1.0.0',
  });
  await writePackage(development, {
    name: 'development-library',
    version: '1.0.0',
  });
  await writePackage(optional, {
    name: 'darwin-only-library',
    version: '1.0.0',
    os: ['darwin'],
  });
  try {
    const locked = await runNpm(root, project, [
      'install',
      '--package-lock-only',
      '--ignore-scripts',
    ]);
    assert.equal(locked.code, 0);
    assert.equal(await pathExists(join(project, 'node_modules')), false);

    const lock = await readJSON(join(project, 'package-lock.json'));
    assert.equal(lock.packages['node_modules/development-library'].link, true);
    assert.equal(lock.packages['node_modules/darwin-only-library'].link, true);
    assert.equal(lock.packages['vendor/development'].dev, true);
    assert.equal(lock.packages['vendor/darwin-only'].optional, true);
    assert.deepEqual(lock.packages['vendor/darwin-only'].os, [
      'darwin',
    ]);

    const installed = await runNpm(root, project, [
      'ci',
      '--omit=dev',
      '--ignore-scripts',
    ]);
    assert.equal(installed.code, 0);
    assert.equal(
      await pathExists(join(project, 'node_modules', 'production-library')),
      true,
    );
    assert.equal(
      await pathExists(join(project, 'node_modules', 'development-library')),
      false,
    );
    assert.equal(
      await pathExists(join(project, 'node_modules', 'darwin-only-library')),
      false,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // omit 只影响磁盘安装，不删除 lock 中的完整解析树；
    // 换平台或 include 时仍可复现。
  },
);

test('npm ls 报告 extraneous，prune dry-run 预览后再删除', async () => {
  const root = await createRoot();
  const project = join(root, 'tree-app');
  const dependency = join(project, 'vendor', 'needed');
  await writePackage(project, {
    name: 'tree-app',
    version: '1.0.0',
    private: true,
    dependencies: {
      'needed-library': 'file:vendor/needed',
    },
  });
  await writePackage(dependency, {
    name: 'needed-library',
    version: '1.0.0',
  });
  try {
    assert.equal((await runNpm(root, project, ['install'])).code, 0);
    await writePackage(join(project, 'node_modules', 'leftover'), {
      name: 'leftover',
      version: '9.9.9',
    });

    const listed = await runNpm(root, project, ['ls', '--json', '--depth=0']);
    assert.equal(listed.code, 0);
    const tree = JSON.parse(listed.stdout);
    assert.match(tree.dependencies.leftover.problems[0], /extraneous/);
    assert.ok(tree.problems.some((problem) => /extraneous.*leftover/.test(problem)));

    const preview = await runNpm(root, project, [
      'prune',
      '--dry-run',
    ]);
    assert.equal(preview.code, 0);
    assert.match(preview.stdout, /remove leftover 9\.9\.9/);
    assert.equal(
      await pathExists(join(project, 'node_modules', 'leftover')),
      true,
    );

    assert.equal((await runNpm(root, project, ['prune'])).code, 0);
    assert.equal(
      await pathExists(join(project, 'node_modules', 'leftover')),
      false,
    );
    assert.equal((await runNpm(root, project, ['ls', '--depth=0'])).code, 0);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('npm uninstall 同时更新清单、lock 和 node_modules', async () => {
  const root = await createRoot();
  const project = join(root, 'uninstall-app');
  const dependency = join(project, 'vendor', 'removable');
  await writePackage(project, {
    name: 'uninstall-app',
    version: '1.0.0',
    private: true,
  });
  await writePackage(dependency, {
    name: 'removable-library',
    version: '1.0.0',
  });
  try {
    assert.equal((await runNpm(root, project, [
      'install',
      './vendor/removable',
    ])).code, 0);
    const removed = await runNpm(root, project, [
      'uninstall',
      'removable-library',
    ]);
    assert.equal(removed.code, 0);
    assert.equal(
      (await readJSON(join(project, 'package.json')))
        .dependencies?.['removable-library'],
      undefined,
    );
    assert.equal(
      (await readJSON(join(project, 'package-lock.json')))
        .packages['node_modules/removable-library'],
      undefined,
    );
    assert.equal(
      await pathExists(join(project, 'node_modules', 'removable-library')),
      false,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // npm 7 起不再执行 uninstall 生命周期脚本，
  // 删除原因过多，无法提供可靠上下文。
});

test(
  'npm shrinkwrap 把根 lock 转成可发布文件，且优先级高于 package-lock',
  async () => {
  const root = await createRoot();
  const project = join(root, 'shrinkwrap-app');
  await writePackage(project, {
    name: 'shrinkwrap-app',
    version: '1.0.0',
    private: true,
  });
  try {
    assert.equal((await runNpm(root, project, [
      'install',
      '--package-lock-only',
    ])).code, 0);
    const original = await readFile(join(project, 'package-lock.json'), 'utf8');
    const wrapped = await runNpm(root, project, ['shrinkwrap']);
    assert.equal(wrapped.code, 0);
    assert.equal(await pathExists(join(project, 'package-lock.json')), false);
    assert.equal(
      await readFile(join(project, 'npm-shrinkwrap.json'), 'utf8'),
      original,
    );

    await cp(
      join(project, 'npm-shrinkwrap.json'),
      join(project, 'package-lock.json'),
    );
    const packageLock = await readJSON(join(project, 'package-lock.json'));
    packageLock.version = '9.9.9';
    await writeFile(
      join(project, 'package-lock.json'),
      JSON.stringify(packageLock, null, 2),
    );
    const installed = await runNpm(root, project, ['ci', '--ignore-scripts']);
    assert.equal(installed.code, 0);
    assert.equal(
      (await readJSON(join(project, 'npm-shrinkwrap.json'))).version,
      '1.0.0',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // 库通常提交 package-lock 即可；只有部署型 CLI 等确实需要
    // 把传递树发布时才 shrinkwrap。
  },
);
