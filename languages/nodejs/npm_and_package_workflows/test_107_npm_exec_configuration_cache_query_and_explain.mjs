// polyglot-covers:
// - nodejs.npm.exec-local-bin-double-hyphen-argument-boundary-and-npx-alias
// - nodejs.npm.exec-package-alternate-bin-call-shell-and-no-install-prompt
// - nodejs.npm.exec-bin-inference-single-name-match-and-ambiguous-error
// - nodejs.npm.exec-workspace-context-selection
// - nodejs.npm.config-cli-environment-project-user-default-precedence
// - nodejs.npm.config-set-get-list-json-delete-and-location-files
// - nodejs.npm.cache-add-ls-verify-content-addressing-and-clean-force
// - nodejs.npm.query-css-direct-prod-leaf-attribute-semver-and-result-count
// - nodejs.npm.explain-dependency-chain-by-name-and-node-modules-path
// - nodejs.npm.fund-local-tree-json-deduplicated-urls-without-opening-browser

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  access,
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

function isolatedNpmEnvironment(root, overrides = {}) {
  return {
    ...process.env,
    HOME: join(root, '.home'),
    NO_COLOR: '1',
    npm_config_audit: 'false',
    npm_config_cache: join(root, '.npm-cache'),
    npm_config_color: 'false',
    npm_config_fund: 'false',
    npm_config_globalconfig: join(root, '.npmrc-global'),
    npm_config_offline: 'true',
    npm_config_prefix: join(root, '.npm-global'),
    npm_config_update_notifier: 'false',
    npm_config_userconfig: join(root, '.npmrc-user'),
    ...overrides,
  };
}

async function runCLI(root, cwd, executable, argumentsList, options = {}) {
  try {
    const result = await execFileAsync(executable, argumentsList, {
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

async function runNpm(root, cwd, argumentsList, options = {}) {
  return runCLI(root, cwd, 'npm', argumentsList, options);
}

async function createRoot(name = 'tooling-app') {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-npm-tooling-'));
  await mkdir(join(root, '.home'));
  await writeFile(join(root, 'package.json'), JSON.stringify({
    name,
    version: '1.0.0',
    private: true,
  }, null, 2));
  return root;
}

async function writePackage(directory, manifest, files = {}) {
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'package.json'),
    JSON.stringify(manifest, null, 2),
  );
  for (const [path, contents] of Object.entries(files)) {
    const target = join(directory, path);
    await mkdir(join(target, '..'), { recursive: true });
    await writeFile(target, contents);
  }
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
  'npm exec 与 npx 都运行本地 bin，参数分界规则不同但结果可一致',
  async () => {
  const root = await createRoot();
  const tool = join(root, 'vendor', 'lesson-tool');
  await writePackage(tool, {
    name: 'lesson-tool',
    version: '1.0.0',
    bin: {
      'lesson-tool': 'cli.mjs',
      'lesson-alt': 'cli.mjs',
    },
  }, {
    'cli.mjs': `#!/usr/bin/env node
process.stdout.write(JSON.stringify({
  arguments: process.argv.slice(2),
  cwd: process.cwd(),
}));
`,
  });
  try {
    assert.equal((await runNpm(root, root, [
      'install',
      './vendor/lesson-tool',
      '--ignore-scripts',
    ])).code, 0);

    const npmExec = await runNpm(root, root, [
      'exec',
      '--',
      'lesson-tool',
      '--package=literal-argument',
      'value',
    ]);
    assert.equal(npmExec.code, 0);
    assert.deepEqual(JSON.parse(npmExec.stdout), {
      arguments: ['--package=literal-argument', 'value'],
      cwd: root,
    });

    const parsedAsNpxOption = await runCLI(root, root, 'npx', [
      '--no',
      'lesson-tool',
      '--package=literal-argument',
      'value',
    ]);
    assert.notEqual(parsedAsNpxOption.code, 0);
    assert.match(parsedAsNpxOption.stderr, /ENOTCACHED.*literal-argument/s);

    const npx = await runCLI(root, root, 'npx', [
      '--no',
      '--',
      'lesson-tool',
      '--package=literal-argument',
      'value',
    ]);
    assert.equal(npx.code, 0, npx.stderr);
    assert.deepEqual(JSON.parse(npx.stdout), {
      arguments: ['--package=literal-argument', 'value'],
      cwd: root,
    });

    const alternate = await runNpm(root, root, [
      'exec',
      '--package=lesson-tool',
      '--',
      'lesson-alt',
      'alternate',
    ]);
    assert.equal(alternate.code, 0);
    assert.deepEqual(JSON.parse(alternate.stdout).arguments, ['alternate']);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
    // npx 的选项必须放在第一个位置参数之前；
    // npm exec 推荐用 -- 明确停止 npm 解析。
  },
);

test('npm exec --call 使用项目工具的 PATH，--no 阻止缺失包下载', async () => {
  const root = await createRoot();
  const binDirectory = join(root, 'node_modules', '.bin');
  await mkdir(binDirectory, { recursive: true });
  await writeFile(join(binDirectory, 'local-command'), `#!/usr/bin/env node
process.stdout.write('called:' + process.argv.slice(2).join(','));
`, { mode: 0o755 });
  try {
    const called = await runNpm(root, root, [
      'exec',
      '--call=local-command first second',
    ]);
    assert.equal(called.code, 0);
    assert.equal(called.stdout, 'called:first,second');

    const refused = await runNpm(root, root, [
      'exec',
      '--no',
      '--',
      'definitely-missing-polyglot-command',
    ]);
    assert.notEqual(refused.code, 0);
    assert.match(
      refused.stderr,
      /ENOTCACHED|canceled|could not determine executable|not found/i,
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // --call 交给平台 shell，适合短组合命令；
  // 复杂逻辑仍应放进可测试的脚本文件。
});

test(
  '位置包名按 bin 启发式推断命令，多入口无法唯一判断时失败',
  async () => {
  const root = await createRoot();
  const single = join(root, 'vendor', 'single-tool');
  const ambiguous = join(root, 'vendor', 'ambiguous-tool');
  await writePackage(single, {
    name: 'single-tool',
    version: '1.0.0',
    bin: { 'only-command': 'cli.mjs' },
  }, {
    'cli.mjs': '#!/usr/bin/env node\nprocess.stdout.write("single");\n',
  });
  await writePackage(ambiguous, {
    name: 'ambiguous-tool',
    version: '1.0.0',
    bin: {
      first: 'first.mjs',
      second: 'second.mjs',
    },
  }, {
    'first.mjs': '#!/usr/bin/env node\n',
    'second.mjs': '#!/usr/bin/env node\n',
  });
  try {
    assert.equal((await runNpm(root, root, [
      'install',
      './vendor/single-tool',
      './vendor/ambiguous-tool',
      '--ignore-scripts',
    ])).code, 0);
    const inferred = await runNpm(root, root, ['exec', '--', 'single-tool']);
    assert.equal(inferred.code, 0);
    assert.equal(inferred.stdout, 'single');

    const failed = await runNpm(root, root, [
      'exec',
      '--',
      'ambiguous-tool',
    ]);
    assert.notEqual(failed.code, 0);
    assert.match(failed.stderr, /could not determine executable to run/i);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  },
);

test(
  'npm exec --workspace 在目标包目录执行，但仍可使用根安装的 bin',
  async () => {
  const root = await createRoot('exec-workspace-root');
  const workspace = join(root, 'packages', 'app');
  const binDirectory = join(root, 'node_modules', '.bin');
  await writeFile(join(root, 'package.json'), JSON.stringify({
    name: 'exec-workspace-root',
    version: '1.0.0',
    private: true,
    workspaces: ['packages/app'],
  }, null, 2));
  await writePackage(workspace, {
    name: '@lesson/exec-app',
    version: '1.0.0',
  });
  await mkdir(binDirectory, { recursive: true });
  await writeFile(join(binDirectory, 'show-cwd'), `#!/usr/bin/env node
process.stdout.write(process.cwd());
`, { mode: 0o755 });
  try {
    const result = await runNpm(root, root, [
      'exec',
      '--workspace=@lesson/exec-app',
      '--',
      'show-cwd',
    ]);
    assert.equal(result.code, 0);
    assert.equal(result.stdout, workspace);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  },
);

test('npm 配置按 CLI、环境、项目、用户、默认值的优先级合并', async () => {
  const root = await createRoot('config-app');
  try {
    const userSet = await runNpm(root, root, [
      'config',
      'set',
      'tag=user-tag',
      '--location=user',
    ]);
    assert.equal(userSet.code, 0);
    assert.match(await readFile(join(root, '.npmrc-user'), 'utf8'), /tag=user-tag/);

    const projectSet = await runNpm(root, root, [
      'config',
      'set',
      'tag=project-tag',
      'save-exact=true',
      '--location=project',
    ]);
    assert.equal(projectSet.code, 0);
    assert.match(await readFile(join(root, '.npmrc'), 'utf8'), /tag=project-tag/);
    assert.equal(
      (await runNpm(root, root, ['config', 'get', 'tag'])).stdout.trim(),
      'project-tag',
    );

    const environment = await runNpm(root, root, ['config', 'get', 'tag'], {
      env: { npm_config_tag: 'environment-tag' },
    });
    assert.equal(environment.stdout.trim(), 'environment-tag');

    const cli = await runNpm(root, root, [
      '--tag=cli-tag',
      'config',
      'get',
      'tag',
    ], { env: { npm_config_tag: 'environment-tag' } });
    assert.equal(cli.stdout.trim(), 'cli-tag');

    const listed = await runNpm(root, root, [
      'config',
      'list',
      '--json',
    ]);
    const config = JSON.parse(listed.stdout);
    assert.equal(config.tag, 'project-tag');
    assert.equal(config['save-exact'], true);
    assert.equal(config.cache, join(root, '.npm-cache'));

    const deleted = await runNpm(root, root, [
      'config',
      'delete',
      'tag',
      '--location=project',
    ]);
    assert.equal(deleted.code, 0);
    assert.equal(
      (await runNpm(root, root, ['config', 'get', 'tag'])).stdout.trim(),
      'user-tag',
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // 认证令牌只能放在对应 registry 的 npmrc 范围，
  // 不能写进 package.json 或测试输出。
});

test('npm cache 可加入本地包、列键并校验；清空必须显式 --force', async () => {
  const root = await createRoot('cache-app');
  const source = join(root, 'cache-source');
  await writePackage(source, {
    name: 'cache-library',
    version: '1.0.0',
    main: 'index.js',
  }, {
    'index.js': 'module.exports = "cached";\n',
  });
  try {
    const packed = await runNpm(root, source, [
      'pack',
      '--json',
      '--pack-destination',
      root,
    ]);
    assert.equal(packed.code, 0);
    const tarball = JSON.parse(packed.stdout)[0].filename;
    const added = await runNpm(root, root, ['cache', 'add', `./${tarball}`]);
    assert.equal(added.code, 0, added.stderr);
    const listed = await runNpm(root, root, ['cache', 'ls']);
    assert.equal(listed.code, 0);
    assert.match(listed.stdout, /cache-source|cache-library/);

    const verified = await runNpm(root, root, ['cache', 'verify']);
    assert.equal(verified.code, 0);
    assert.match(verified.stdout, /Cache verified and compressed/);
    assert.match(verified.stdout, /Content verified:/);

    const refused = await runNpm(root, root, ['cache', 'clean']);
    assert.notEqual(refused.code, 0);
    assert.match(refused.stderr, /As of npm@5, the npm cache self-heals/);
    const cleaned = await runNpm(root, root, ['cache', 'clean', '--force']);
    assert.equal(cleaned.code, 0);
    assert.equal(await pathExists(join(root, '.npm-cache', '_cacache')), false);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // cache 是可校验的内容寻址缓存，不是持久仓库；
  // 损坏时 npm 会报错或重新获取。
});

async function createQueryTree() {
  const root = await createRoot('query-app');
  const leaf = join(root, 'vendor', 'leaf-library');
  const middle = join(root, 'vendor', 'middle-library');
  await writePackage(leaf, {
    name: 'leaf-library',
    version: '1.2.3',
    license: 'MIT',
    funding: 'https://example.test/shared-funding',
  });
  await writePackage(middle, {
    name: 'middle-library',
    version: '2.0.0',
    license: 'Apache-2.0',
    funding: 'https://example.test/shared-funding',
    dependencies: {
      'leaf-library': 'file:../leaf-library',
    },
  });
  const manifest = JSON.parse(await readFile(join(root, 'package.json')));
  manifest.dependencies = {
    'middle-library': 'file:vendor/middle-library',
  };
  await writeFile(join(root, 'package.json'), JSON.stringify(manifest, null, 2));
  const installed = await runNpm(root, root, ['install', '--ignore-scripts']);
  assert.equal(installed.code, 0);
  return root;
}

test('npm query 用 CSS 选择器筛依赖，并可把结果数量当 CI 断言', async () => {
  const root = await createQueryTree();
  try {
    const direct = await runNpm(root, root, ['query', ':root > .prod']);
    assert.equal(direct.code, 0);
    assert.deepEqual(
      JSON.parse(direct.stdout).map(({ name }) => name),
      ['middle-library', 'leaf-library'],
    );

    const leaves = await runNpm(root, root, ['query', ':empty']);
    assert.ok(
      JSON.parse(leaves.stdout).some(({ name }) => name === 'leaf-library'),
    );
    const licensed = await runNpm(root, root, ['query', '[license=MIT]']);
    assert.deepEqual(
      JSON.parse(licensed.stdout).map(({ name }) => name),
      ['leaf-library'],
    );
    const semver = await runNpm(root, root, [
      'query',
      '[name="leaf-library"]:semver(^1.0.0)',
      '--expect-result-count=1',
    ]);
    assert.equal(semver.code, 0, semver.stderr);

    const wrongCount = await runNpm(root, root, [
      'query',
      '#leaf-library',
      '--expect-result-count=2',
    ]);
    assert.notEqual(wrongCount.code, 0);
    assert.match(wrongCount.stderr, /Expected 2 results, got 1/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test(
  'npm explain 展示引入链，fund --json 汇总本地 funding 而不打开浏览器',
  async () => {
  const root = await createQueryTree();
  try {
    const byName = await runNpm(root, root, ['explain', 'leaf-library']);
    assert.equal(byName.code, 0);
    assert.match(byName.stdout, /leaf-library@1\.2\.3/);
    assert.match(byName.stdout, /middle-library@2\.0\.0/);
    assert.match(byName.stdout, /from the root project/);

    const byPath = await runNpm(root, root, [
      'explain',
      'node_modules/leaf-library',
    ]);
    assert.equal(byPath.code, 0);
    assert.match(byPath.stdout, /leaf-library@1\.2\.3/);

    const funded = await runNpm(root, root, ['fund', '--json']);
    assert.equal(funded.code, 0);
    const serialized = JSON.stringify(JSON.parse(funded.stdout));
    assert.match(serialized, /https:\/\/example\.test\/shared-funding/);
    assert.match(serialized, /middle-library/);
    assert.match(serialized, /leaf-library/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
  // `npm fund <name>` 会尝试打开浏览器；自动化中使用无包名的列表或 --json。
  },
);
