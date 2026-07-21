// polyglot-covers:
// - nodejs.npm.pack-dry-run-json-name-version-size-integrity-shasum-and-files
// - nodejs.npm.pack-files-whitelist-main-bin-readme-license-always-included
// - nodejs.npm.pack-npmignore-gitignore-precedence-subdirectory-and-negation
// - nodejs.npm.pack-always-excluded-lock-config-vcs-and-symbolic-links
// - nodejs.npm.pack-prepack-prepare-postpack-order-and-generated-output
// - nodejs.npm.pack-destination-tarball-local-install-and-bin-link
// - nodejs.npm.bundle-dependencies-node-modules-content-and-pack-metadata
// - nodejs.npm.publish-dry-run-lifecycle-preview-access-tag-and-no-registry-write
// - nodejs.npm.publish-private-manifest-guard-and-dry-run-limitation
// - nodejs.npm.pkg-fix-publish-normalization-without-hand-editing

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  access,
  chmod,
  mkdir,
  mkdtemp,
  readFile,
  readlink,
  rm,
  symlink,
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
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-npm-pack-'));
  await mkdir(join(root, '.home'));
  return root;
}

async function writeJSON(path, value) {
  await writeFile(path, JSON.stringify(value, null, 2));
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

function packedPaths(result) {
  return result.files.map(({ path }) => path).sort();
}

test('npm pack --dry-run 精确预览白名单、强制包含项和强制排除项', async () => {
  const root = await createRoot();
  const project = join(root, 'archive');
  await mkdir(join(project, 'dist'), { recursive: true });
  await mkdir(join(project, 'src'));
  await mkdir(join(project, 'bin'));
  await mkdir(join(project, '.git'));
  await writeJSON(join(project, 'package.json'), {
    name: '@lesson/archive',
    version: '1.2.3',
    description: 'pack contents lesson',
    license: 'MIT',
    files: ['dist'],
    main: 'src/main.js',
    bin: { lesson: 'bin/cli.js' },
  });
  await writeFile(join(project, 'README.md'), '# Archive lesson\n');
  await writeFile(join(project, 'LICENSE.txt'), 'MIT lesson text\n');
  await writeFile(join(project, 'src/main.js'), 'module.exports = 42;\n');
  await writeFile(join(project, 'bin/cli.js'), '#!/usr/bin/env node\n');
  await writeFile(join(project, 'dist/public.js'), 'export const value = 42;\n');
  await writeFile(join(project, 'dist/secret.js'), 'export const secret = true;\n');
  await writeFile(join(project, 'dist/keep.tmp'), 'included by negation\n');
  await writeFile(join(project, 'dist/drop.tmp'), 'excluded tmp\n');
  await writeFile(join(project, 'dist/.npmignore'), 'secret.js\n*.tmp\n!keep.tmp\n');
  await writeFile(join(project, 'extra.txt'), 'not in files whitelist\n');
  await writeFile(join(project, '.gitignore'), 'dist/public.js\nREADME.md\n');
  await writeFile(join(project, '.npmignore'), '# overrides root .gitignore\n');
  await writeFile(join(project, '.npmrc'), 'registry=http://example.invalid\n');
  await writeFile(join(project, 'package-lock.json'), '{}\n');
  await writeFile(join(project, '.git/config'), 'not a repository\n');
  await symlink('dist/public.js', join(project, 'public-link.js'));

  try {
    const preview = await runNpm(root, project, [
      'pack',
      '--dry-run',
      '--json',
    ]);
    assert.equal(preview.code, 0);
    const [result] = JSON.parse(preview.stdout);
    assert.equal(result.id, '@lesson/archive@1.2.3');
    assert.equal(result.name, '@lesson/archive');
    assert.equal(result.version, '1.2.3');
    assert.equal(result.filename, 'lesson-archive-1.2.3.tgz');
    assert.match(result.integrity, /^sha512-/);
    assert.match(result.shasum, /^[0-9a-f]{40}$/);
    assert.ok(result.size > 0);
    assert.ok(result.unpackedSize > 0);
    assert.deepEqual(packedPaths(result), [
      'LICENSE.txt',
      'README.md',
      'bin/cli.js',
      'dist/keep.tmp',
      'dist/public.js',
      'package.json',
      'src/main.js',
    ]);
    assert.equal(await pathExists(join(project, result.filename)), false);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // 根 .npmignore 存在时 .gitignore 不参与；子目录 .npmignore 仍能缩小 files
  // 已允许的目录。package-lock、.npmrc、VCS 元数据和符号链接不会进入包。
});

test(
  'pack 生命周期可生成产物，实际 tarball 能离线安装并创建 bin 链接',
  async () => {
  const root = await createRoot();
  const project = join(root, 'generated-tool');
  const destination = join(root, 'tarballs');
  const consumer = join(root, 'consumer');
  const log = join(root, 'pack-lifecycle.log');
  await mkdir(project);
  await mkdir(destination);
  await mkdir(consumer);
  await writeFile(join(project, 'lifecycle.mjs'), `
    import { appendFileSync, mkdirSync, writeFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, process.env.npm_lifecycle_event + '\\n');
    if (process.env.npm_lifecycle_event === 'prepare') {
      mkdirSync('dist', { recursive: true });
      writeFileSync('dist/index.js', 'export const answer = 42;\\n');
    }
  `);
  await writeFile(join(project, 'bin.mjs'), `#!/usr/bin/env node
process.stdout.write('packed-cli:' + process.argv.slice(2).join(','));
`);
  await chmod(join(project, 'bin.mjs'), 0o755);
  await writeJSON(join(project, 'package.json'), {
    name: 'generated-tool',
    version: '2.0.0',
    type: 'module',
    exports: './dist/index.js',
    bin: { 'generated-tool': './bin.mjs' },
    files: ['dist', 'bin.mjs'],
    scripts: {
      prepack: 'node lifecycle.mjs',
      prepare: 'node lifecycle.mjs',
      postpack: 'node lifecycle.mjs',
    },
  });
  await writeJSON(join(consumer, 'package.json'), {
    name: 'pack-consumer',
    version: '1.0.0',
    private: true,
  });
  try {
    const packed = await runNpm(root, project, [
      'pack',
      '--json',
      '--foreground-scripts',
      '--pack-destination',
      destination,
    ], { env: { LOG_FILE: log } });
    assert.equal(packed.code, 0);
    const [metadata] = JSON.parse(packed.stdout);
    assert.ok(packedPaths(metadata).includes('dist/index.js'));
    assert.deepEqual((await readFile(log, 'utf8')).trim().split('\n'), [
      'prepack',
      'prepare',
      'postpack',
    ]);
    const tarball = join(destination, metadata.filename);
    assert.equal(await pathExists(tarball), true);

    const installed = await runNpm(root, consumer, [
      'install',
      tarball,
      '--ignore-scripts',
    ]);
    assert.equal(installed.code, 0);
    const imported = await execFileAsync(process.execPath, [
      '--input-type=module',
      '--eval',
      `import('generated-tool').then(({ answer }) => {
        process.stdout.write(String(answer));
      });`,
    ], { cwd: consumer, encoding: 'utf8' });
    assert.equal(imported.stdout, '42');
    const binLink = join(consumer, 'node_modules', '.bin', 'generated-tool');
    assert.match(await readlink(binLink), /generated-tool\/bin\.mjs$/);
    const executed = await execFileAsync(binLink, ['first', 'second'], {
      cwd: consumer,
      encoding: 'utf8',
    });
    assert.equal(executed.stdout, 'packed-cli:first,second');
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // dry-run 也执行 pack 生命周期；只想静态列文件时，
    // 脚本仍可能产生副作用。
  },
);

test(
  'bundleDependencies 把已安装依赖内容嵌入 tarball，并在元数据列出',
  async () => {
  const root = await createRoot();
  const project = join(root, 'bundled-tool');
  const dependency = join(project, 'vendor', 'bundled-library');
  await mkdir(dependency, { recursive: true });
  await writeJSON(join(dependency, 'package.json'), {
    name: 'bundled-library',
    version: '1.0.0',
    main: 'index.js',
  });
  await writeFile(join(dependency, 'index.js'), 'module.exports = "bundled";\n');
  await writeJSON(join(project, 'package.json'), {
    name: 'bundled-tool',
    version: '1.0.0',
    main: 'index.js',
    dependencies: {
      'bundled-library': 'file:vendor/bundled-library',
    },
    bundleDependencies: ['bundled-library'],
  });
  await writeFile(
    join(project, 'index.js'),
    'module.exports = require("bundled-library");\n',
  );
  try {
    assert.equal((await runNpm(root, project, [
      'install',
      '--ignore-scripts',
    ])).code, 0);
    const preview = await runNpm(root, project, [
      'pack',
      '--dry-run',
      '--json',
      '--ignore-scripts',
    ]);
    assert.equal(preview.code, 0);
    const [metadata] = JSON.parse(preview.stdout);
    assert.deepEqual(metadata.bundled, ['bundled-library']);
    assert.ok(
      packedPaths(metadata)
        .includes('node_modules/bundled-library/index.js'),
    );
    assert.equal(packedPaths(metadata).includes('package-lock.json'), false);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // bundled 依赖增大 tarball，但能把部署所需版本一起交付；
  // 普通 node_modules 始终排除，只有 bundleDependencies 指定项例外。
  },
);

test(
  'publish --dry-run 执行发布生命周期并返回上传预览，但不写 registry',
  async () => {
  const root = await createRoot();
  const project = join(root, 'publish-preview');
  const log = join(root, 'publish-lifecycle.log');
  await mkdir(project);
  await writeFile(join(project, 'record.mjs'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, process.env.npm_lifecycle_event + '\\n');
  `);
  const record = 'node record.mjs';
  await writeJSON(join(project, 'package.json'), {
    name: '@lesson/publish-preview',
    version: '3.1.4',
    description: 'publish dry run lesson',
    license: 'MIT',
    main: 'index.js',
    scripts: {
      prepublishOnly: record,
      prepack: record,
      prepare: record,
      postpack: record,
      publish: record,
      postpublish: record,
    },
  });
  await writeFile(join(project, 'index.js'), 'module.exports = 314;\n');
  try {
    const preview = await runNpm(root, project, [
      'publish',
      '--dry-run',
      '--json',
      '--access=public',
      '--tag=next',
      '--foreground-scripts',
    ], { env: { LOG_FILE: log } });
    assert.equal(preview.code, 0);
    const output = JSON.parse(preview.stdout);
    const metadata = output['@lesson/publish-preview'];
    assert.deepEqual(Object.keys(output), ['@lesson/publish-preview']);
    assert.equal(metadata.id, '@lesson/publish-preview@3.1.4');
    assert.equal(metadata.name, '@lesson/publish-preview');
    assert.equal(metadata.version, '3.1.4');
    assert.match(metadata.integrity, /^sha512-/);
    assert.ok(metadata.files.some(({ path }) => path === 'index.js'));
    assert.deepEqual((await readFile(log, 'utf8')).trim().split('\n'), [
      'prepublishOnly',
      'prepack',
      'prepare',
      'postpack',
      'publish',
      'postpublish',
    ]);
    assert.equal(await pathExists(join(project, metadata.filename)), false);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // dry-run 不上传，但生命周期仍执行。真实发布还要确认 registry、
    // scope access、dist-tag、认证与 OTP；同一 name@version 即使 unpublish
    // 也不能再次使用。
  },
);

test(
  'private 会阻止真实 publish，但 dry-run 只做打包预览并绕过该保护',
  async () => {
  const root = await createRoot();
  const project = join(root, 'private-app');
  await mkdir(project);
  await writeJSON(join(project, 'package.json'), {
    name: 'private-app',
    version: '1.0.0',
    private: true,
  });
  try {
    const result = await runNpm(root, project, ['publish', '--dry-run']);
    assert.equal(result.code, 0);
    assert.match(result.stdout, /\+ private-app@1\.0\.0/);
    assert.match(result.stderr, /Publishing to .* with tag latest.*dry-run/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // private 仍是实际上传的重要保险，但 dry-run 不进入上传阶段，
  // 因而不能把本测试的成功误读为 private 包可以真正发布。
});

test('npm pkg fix 把发布时会修正的 repository 简写提前正规化', async () => {
  const root = await createRoot();
  const project = join(root, 'fix-manifest');
  await mkdir(project);
  await writeJSON(join(project, 'package.json'), {
    name: 'fix-manifest',
    version: '1.0.0',
    repository: 'npm/example',
  });
  try {
    const fixed = await runNpm(root, project, ['pkg', 'fix']);
    assert.equal(fixed.code, 0);
    const manifest = JSON.parse(await readFile(join(project, 'package.json')));
    assert.deepEqual(manifest.repository, {
      type: 'git',
      url: 'git+https://github.com/npm/example.git',
    });
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // 把自动修正写回源码，可避免 publish 时上传的清单
    // 与 Git 中看到的内容不同。
  },
);
