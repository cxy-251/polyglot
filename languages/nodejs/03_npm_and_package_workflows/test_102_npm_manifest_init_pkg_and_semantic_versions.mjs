// polyglot-covers:
// - nodejs.npm.cli-version-locked-runtime-and-isolated-home-cache
// - nodejs.npm.init-yes-default-manifest-and-scoped-name
// - nodejs.npm.pkg-get-multiple-nested-array-and-bracket-fields
// - nodejs.npm.pkg-set-string-json-number-boolean-array-and-multiple-fields
// - nodejs.npm.pkg-delete-and-format-preservation
// - nodejs.npm.version-semver-increments-prerelease-and-no-git-tag-version
// - nodejs.npm.version-package-lock-synchronization-and-same-version-error
// - nodejs.npm.manifest-private-engines-files-bin-funding-and-package-manager-metadata

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

function isolatedNpmEnvironment(project, overrides = {}) {
  return {
    ...process.env,
    HOME: join(project, '.home'),
    NO_COLOR: '1',
    npm_config_audit: 'false',
    npm_config_cache: join(project, '.npm-cache'),
    npm_config_color: 'false',
    npm_config_fund: 'false',
    npm_config_offline: 'true',
    npm_config_update_notifier: 'false',
    npm_config_userconfig: join(project, '.npmrc-user'),
    ...overrides,
  };
}

async function runNpm(project, argumentsList, options = {}) {
  try {
    const result = await execFileAsync('npm', argumentsList, {
      cwd: project,
      encoding: 'utf8',
      env: isolatedNpmEnvironment(project, options.env),
      ...options,
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

async function createProject() {
  const project = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-npm-manifest-'));
  await mkdir(join(project, '.home'));
  return project;
}

async function readJSON(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

test('npm 使用锁定版本，并把 HOME 与缓存限制在测试临时目录', async () => {
  const project = await createProject();
  try {
    const version = await runNpm(project, ['--version']);
    assert.equal(version.code, 0);
    assert.equal(version.stdout.trim(), '11.16.0');

    const cache = await runNpm(project, ['config', 'get', 'cache']);
    assert.equal(cache.code, 0);
    assert.equal(cache.stdout.trim(), join(project, '.npm-cache'));
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // npm 会读取用户级配置和缓存；案例主动隔离，
  // 避免结果依赖真实主机状态。
});

test('npm init --yes 生成最小清单，scope 只改变包名而不联网', async () => {
  const project = await createProject();
  try {
    const initialized = await runNpm(project, [
      'init',
      '--yes',
      '--scope=@polyglot',
      '--init-private=true',
    ]);
    assert.equal(initialized.code, 0);
    const manifest = await readJSON(join(project, 'package.json'));
    assert.equal(
      manifest.name,
      `@polyglot/${project.split('/').at(-1).toLowerCase()}`,
    );
    assert.equal(manifest.version, '1.0.0');
    assert.equal(manifest.main, 'index.js');
    assert.equal(manifest.private, true);
    assert.match(manifest.scripts.test, /no test specified/);
    assert.deepEqual(manifest.keywords, []);
    assert.equal(manifest.license, 'ISC');
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 带 initializer 的 npm init 会转成 npm exec 并可能访问 registry；
  // 纯 `init --yes` 才是无需下载的 legacy 初始化流程。
});

test('npm pkg set 支持嵌套字段、数组索引和 JSON 类型', async () => {
  const project = await createProject();
  const manifestPath = join(project, 'package.json');
  await writeFile(manifestPath, JSON.stringify({
    name: 'manifest-lesson',
    version: '1.2.3',
  }, null, 2));
  try {
    const strings = await runNpm(project, [
      'pkg',
      'set',
      'description=可查询的 npm 清单案例',
      'engines.node=>=24',
      'bin.polyglot=bin/cli.js',
      'contributors[0].name=Ada',
      'contributors[0].email=ada@example.test',
      'files[0]=dist',
      'files[1]=README.md',
    ]);
    assert.equal(strings.code, 0);

    const typed = await runNpm(project, [
      'pkg',
      'set',
      'private=true',
      'config.port=8080',
      'funding=[{"type":"individual","url":"https://example.test/fund"}]',
      '--json',
    ]);
    assert.equal(typed.code, 0);

    const manifest = await readJSON(manifestPath);
    assert.equal(manifest.description, '可查询的 npm 清单案例');
    assert.deepEqual(manifest.engines, { node: '>=24' });
    assert.deepEqual(manifest.bin, { polyglot: 'bin/cli.js' });
    assert.deepEqual(manifest.contributors, [{
      name: 'Ada',
      email: 'ada@example.test',
    }]);
    assert.deepEqual(manifest.files, ['dist', 'README.md']);
    assert.equal(manifest.private, true);
    assert.equal(manifest.config.port, 8080);
    assert.deepEqual(manifest.funding, [{
      type: 'individual',
      url: 'https://example.test/fund',
    }]);
    assert.match(await readFile(manifestPath, 'utf8'), /^\{\n  "name"/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 未加 --json 时所有右值都是字符串；布尔值、数字、数组必须显式请求
  // JSON 解析。
});

test('npm pkg get 总返回 JSON，可一次读取多个字段和数组投影', async () => {
  const project = await createProject();
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'query-lesson',
    version: '2.0.0',
    exports: {
      '.': {
        import: './dist/index.mjs',
        require: './dist/index.cjs',
      },
    },
    contributors: [
      { name: 'Ada', email: 'ada@example.test' },
      { name: 'Linus', email: 'linus@example.test' },
    ],
  }, null, 2));
  try {
    const multiple = await runNpm(project, [
      'pkg',
      'get',
      'name',
      'version',
      'exports[.].require',
    ]);
    assert.equal(multiple.code, 0);
    assert.deepEqual(JSON.parse(multiple.stdout), {
      name: 'query-lesson',
      version: '2.0.0',
      'exports[.].require': './dist/index.cjs',
    });

    const emails = await runNpm(project, ['pkg', 'get', 'contributors.email']);
    assert.deepEqual(JSON.parse(emails.stdout), {
      'contributors[0].email': 'ada@example.test',
      'contributors[1].email': 'linus@example.test',
    });
    const first = await runNpm(project, ['pkg', 'get', 'contributors[0].email']);
    assert.equal(JSON.parse(first.stdout), 'ada@example.test');
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test('npm pkg delete 精确删除字段，并保留同级配置', async () => {
  const project = await createProject();
  const manifestPath = join(project, 'package.json');
  await writeFile(manifestPath, JSON.stringify({
    name: 'delete-lesson',
    version: '1.0.0',
    scripts: {
      build: 'node build.js',
      test: 'node --test',
    },
    config: {
      port: 8080,
      mode: 'study',
    },
  }, null, 2));
  try {
    const deleted = await runNpm(project, [
      'pkg',
      'delete',
      'scripts.build',
      'config.port',
    ]);
    assert.equal(deleted.code, 0);
    assert.deepEqual(await readJSON(manifestPath), {
      name: 'delete-lesson',
      version: '1.0.0',
      scripts: { test: 'node --test' },
      config: { mode: 'study' },
    });
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test('npm version 按 semver 递增，并同步 package-lock 而不创建 Git 标签', async () => {
  const project = await createProject();
  const manifestPath = join(project, 'package.json');
  const lockPath = join(project, 'package-lock.json');
  await writeFile(manifestPath, JSON.stringify({
    name: 'version-lesson',
    version: '1.2.3',
    private: true,
  }, null, 2));
  try {
    const locked = await runNpm(project, ['install', '--package-lock-only']);
    assert.equal(locked.code, 0);

    const preminor = await runNpm(project, [
      'version',
      'preminor',
      '--preid=beta',
      '--no-git-tag-version',
    ]);
    assert.equal(preminor.code, 0);
    assert.equal(preminor.stdout.trim(), 'v1.3.0-beta.0');
    assert.equal((await readJSON(manifestPath)).version, '1.3.0-beta.0');
    assert.equal((await readJSON(lockPath)).version, '1.3.0-beta.0');
    assert.equal((await readJSON(lockPath)).packages[''].version, '1.3.0-beta.0');

    const prerelease = await runNpm(project, [
      'version',
      'prerelease',
      '--preid=beta',
      '--no-git-tag-version',
    ]);
    assert.equal(prerelease.stdout.trim(), 'v1.3.0-beta.1');

    const stable = await runNpm(project, [
      'version',
      'patch',
      '--no-git-tag-version',
    ]);
    assert.equal(stable.stdout.trim(), 'v1.3.0');

    const unchanged = await runNpm(project, [
      'version',
      '1.3.0',
      '--no-git-tag-version',
    ]);
    assert.equal(unchanged.code, 1);
    assert.match(unchanged.stderr, /Version not changed/);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 默认 npm version 会在 Git 仓库创建 commit 和 tag；
  // 教学案例显式关闭该副作用。
});

test(
  '发布相关元数据各自控制安装、打包和工具提示，不等同于运行时 exports',
  async () => {
  const project = await createProject();
  const manifest = {
    name: '@polyglot/metadata-lesson',
    version: '1.0.0',
    private: true,
    packageManager: 'npm@11.16.0',
    engines: { node: '>=24 <25', npm: '^11.16.0' },
    os: ['linux', 'darwin'],
    cpu: ['x64', 'arm64'],
    files: ['dist', 'README.md'],
    bin: { polyglot: './bin/cli.js' },
    funding: 'https://example.test/fund',
    exports: { '.': './dist/index.js' },
  };
  await writeFile(join(project, 'package.json'), JSON.stringify(manifest, null, 2));
  try {
    const queried = await runNpm(project, [
      'pkg',
      'get',
      'private',
      'packageManager',
      'engines',
      'files',
      'bin',
    ]);
    assert.equal(queried.code, 0);
    assert.deepEqual(JSON.parse(queried.stdout), {
      private: true,
      packageManager: 'npm@11.16.0',
      engines: { node: '>=24 <25', npm: '^11.16.0' },
      files: ['dist', 'README.md'],
      bin: { polyglot: './bin/cli.js' },
    });
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // private 阻止误发布；files 选择 tarball；bin 创建命令入口；
  // engines/os/cpu 描述兼容性。模块可见性仍由 exports 单独决定。
  },
);
