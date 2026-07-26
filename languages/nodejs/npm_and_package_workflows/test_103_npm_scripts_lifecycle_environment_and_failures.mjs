// polyglot-covers:
// - nodejs.npm.run-user-script-pre-main-post-order-and-argument-forwarding
// - nodejs.npm.run-script-package-root-init-cwd-and-lifecycle-environment
// - nodejs.npm.run-local-node-modules-bin-path-precedence
// - nodejs.npm.run-missing-script-if-present-and-nonzero-abort
// - nodejs.npm.start-default-server-js-and-restart-fallback-sequence
// - nodejs.npm.install-lifecycle-order-foreground-scripts-and-ignore-scripts
// - nodejs.npm.version-pre-version-post-order-old-new-environment
// - nodejs.npm.script-shell-platform-boundary-and-node-script-portability

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  chmod,
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
  const {
    cwd = project,
    env = {},
    ...execOptions
  } = options;
  try {
    const result = await execFileAsync('npm', argumentsList, {
      cwd,
      encoding: 'utf8',
      env: isolatedNpmEnvironment(project, env),
      ...execOptions,
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

async function createProject(name = 'scripts-lesson') {
  const project = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-npm-scripts-'));
  await mkdir(join(project, '.home'));
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name,
    version: '1.2.3',
    private: true,
  }, null, 2));
  return project;
}

async function writeRecorder(project) {
  await writeFile(join(project, 'record.mjs'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, JSON.stringify({
      event: process.env.npm_lifecycle_event,
      command: process.env.npm_command,
      script: process.env.npm_lifecycle_script,
      packageName: process.env.npm_package_name,
      packageVersion: process.env.npm_package_version,
      packageJSON: process.env.npm_package_json,
      packageMode: process.env.npm_package_config_mode,
      initCwd: process.env.INIT_CWD,
      cwd: process.cwd(),
      oldVersion: process.env.npm_old_version,
      newVersion: process.env.npm_new_version,
      arguments: process.argv.slice(2),
    }) + '\\n');
  `);
}

async function readRecords(path) {
  const text = await readFile(path, 'utf8');
  return text.trim().split('\n').map((line) => JSON.parse(line));
}

test('npm run 自动包围 pre/post 脚本，-- 后参数只传给主脚本', async () => {
  const project = await createProject();
  const log = join(project, 'events.jsonl');
  await writeRecorder(project);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'scripts-lesson',
    version: '1.2.3',
    private: true,
    config: { mode: 'study' },
    scripts: {
      prebuild: 'node record.mjs pre-argument',
      build: 'node record.mjs',
      postbuild: 'node record.mjs post-argument',
    },
  }, null, 2));
  try {
    const result = await runNpm(project, [
      'run',
      'build',
      '--',
      '--target',
      'demo',
    ], { env: { LOG_FILE: log } });
    assert.equal(result.code, 0);
    const records = await readRecords(log);
    assert.deepEqual(records.map(({ event }) => event), [
      'prebuild',
      'build',
      'postbuild',
    ]);
    assert.deepEqual(
      records.map(({ arguments: scriptArguments }) => scriptArguments),
      [
      ['pre-argument'],
      ['--target', 'demo'],
      ['post-argument'],
      ],
    );
    assert.ok(records.every(({ packageName }) => packageName === 'scripts-lesson'));
    assert.ok(records.every(({ packageVersion }) => packageVersion === '1.2.3'));
    assert.ok(records.every(({ packageMode }) => packageMode === 'study'));
    assert.ok(records.every(({ command }) => command === 'run'));
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // `npm run pack` 是名为 pack 的用户脚本，与真正生成 tarball 的 `npm pack`
  // 没有关系；命令语义由是否带 run 决定。
});

test('脚本 cwd 固定为包根，INIT_CWD 保留调用 npm 时所在目录', async () => {
  const project = await createProject();
  const nested = join(project, 'docs', 'examples');
  const log = join(project, 'environment.jsonl');
  await mkdir(nested, { recursive: true });
  await writeRecorder(project);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'cwd-lesson',
    version: '1.0.0',
    private: true,
    scripts: { inspect: 'node record.mjs' },
  }, null, 2));
  try {
    const result = await runNpm(project, ['run', 'inspect'], {
      cwd: nested,
      env: { LOG_FILE: log },
    });
    assert.equal(result.code, 0);
    const [record] = await readRecords(log);
    assert.equal(record.cwd, project);
    assert.equal(record.initCwd, nested);
    assert.equal(record.packageJSON, join(project, 'package.json'));
    assert.equal(record.script, 'node record.mjs');
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 不要用脚本 cwd 猜用户从哪里发起命令；需要这个信息时读取 INIT_CWD。
});

test('npm run 把 node_modules/.bin 放到 PATH，依赖命令无需写绝对路径', async () => {
  const project = await createProject();
  const binDirectory = join(project, 'node_modules', '.bin');
  const executable = join(binDirectory, 'lesson-tool');
  await mkdir(binDirectory, { recursive: true });
  await writeFile(executable, `#!/usr/bin/env node
process.stdout.write(JSON.stringify({
  arguments: process.argv.slice(2),
  lifecycle: process.env.npm_lifecycle_event,
}));
`);
  await chmod(executable, 0o755);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'bin-path-lesson',
    version: '1.0.0',
    private: true,
    scripts: { inspect: 'lesson-tool first second' },
  }, null, 2));
  try {
    const result = await runNpm(project, ['run', '--silent', 'inspect']);
    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.stdout), {
      arguments: ['first', 'second'],
      lifecycle: 'inspect',
    });
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // PATH 注入会逐级包含父目录的 node_modules/.bin；
  // 同名工具可能被更近的包遮蔽。
});

test('缺失脚本可用 --if-present 忽略，非零退出会阻止 post 阶段', async () => {
  const project = await createProject();
  const log = join(project, 'failures.jsonl');
  await writeFile(join(project, 'write-event.mjs'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, process.argv[2] + '\\n');
    if (process.argv[2] === 'main') process.exitCode = 7;
  `);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'failure-lesson',
    version: '1.0.0',
    private: true,
    scripts: {
      prefail: 'node write-event.mjs pre',
      fail: 'node write-event.mjs main',
      postfail: 'node write-event.mjs post',
    },
  }, null, 2));
  try {
    const missing = await runNpm(project, ['run', 'missing']);
    assert.equal(missing.code, 1);
    assert.match(missing.stderr, /Missing script: "missing"/);

    const optional = await runNpm(project, ['run', 'missing', '--if-present']);
    assert.equal(optional.code, 0);
    assert.equal(optional.stdout, '');

    const failure = await runNpm(project, ['run', '--silent', 'fail'], {
      env: { LOG_FILE: log },
    });
    assert.equal(failure.code, 7);
    assert.deepEqual((await readFile(log, 'utf8')).trim().split('\n'), [
      'pre',
      'main',
    ]);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
});

test(
  '缺少 start 字段时默认执行 server.js，restart 回退到 stop 再 start',
  async () => {
  const project = await createProject();
  const log = join(project, 'restart.jsonl');
  await writeFile(join(project, 'write-event.mjs'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, process.env.npm_lifecycle_event + '\\n');
  `);
  await writeFile(join(project, 'server.js'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, 'server.js\\n');
  `);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'restart-lesson',
    version: '1.0.0',
    private: true,
    type: 'module',
    scripts: {
      prestop: 'node write-event.mjs',
      stop: 'node write-event.mjs',
      poststop: 'node write-event.mjs',
      prestart: 'node write-event.mjs',
      poststart: 'node write-event.mjs',
    },
  }, null, 2));
  try {
    const started = await runNpm(project, ['start', '--silent'], {
      env: { LOG_FILE: log },
    });
    assert.equal(started.code, 0);
    assert.deepEqual((await readFile(log, 'utf8')).trim().split('\n'), [
      'prestart',
      'server.js',
      'poststart',
    ]);

    await rm(log, { force: true });
    const restarted = await runNpm(project, ['restart', '--silent'], {
      env: { LOG_FILE: log },
    });
    assert.equal(restarted.code, 0);
    assert.deepEqual((await readFile(log, 'utf8')).trim().split('\n'), [
      'prestop',
      'stop',
      'poststop',
      'prestart',
      'server.js',
      'poststart',
    ]);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
    // 一旦显式声明 restart，npm 就只执行 pre/restart/postrestart，
    // 不再回退组合命令。
  },
);

test('npm install 生命周期有固定顺序，--ignore-scripts 可完全跳过', async () => {
  const project = await createProject();
  const log = join(project, 'install.jsonl');
  await writeFile(join(project, 'record-stage.mjs'), `
    import { appendFileSync } from 'node:fs';
    appendFileSync(process.env.LOG_FILE, process.env.npm_lifecycle_event + '\\n');
  `);
  const stageCommand = 'node record-stage.mjs';
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'install-lifecycle-lesson',
    version: '1.0.0',
    private: true,
    scripts: Object.fromEntries([
      'preinstall',
      'install',
      'postinstall',
      'prepublish',
      'preprepare',
      'prepare',
      'postprepare',
    ].map((stage) => [stage, stageCommand])),
  }, null, 2));
  try {
    const installed = await runNpm(project, [
      'install',
      '--foreground-scripts',
    ], { env: { LOG_FILE: log } });
    assert.equal(installed.code, 0);
    assert.deepEqual((await readFile(log, 'utf8')).trim().split('\n'), [
      'preinstall',
      'install',
      'postinstall',
      'prepublish',
      'preprepare',
      'prepare',
      'postprepare',
    ]);

    await rm(log, { force: true });
    const ignored = await runNpm(project, ['install', '--ignore-scripts'], {
      env: { LOG_FILE: log },
    });
    assert.equal(ignored.code, 0);
    await assert.rejects(readFile(log), (error) => error.code === 'ENOENT');
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // prepare 在 npm 7+ 默认后台运行；调试输出时用 --foreground-scripts，
  // CI 安全审查或安装不可信包时可用 --ignore-scripts 禁止生命周期代码。
});

test(
  'npm version 生命周期可观察旧版与新版，并按 pre/version/post 排序',
  async () => {
  const project = await createProject();
  const log = join(project, 'versions.jsonl');
  await writeRecorder(project);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'version-hooks-lesson',
    version: '1.2.3',
    private: true,
    scripts: {
      preversion: 'node record.mjs',
      version: 'node record.mjs',
      postversion: 'node record.mjs',
    },
  }, null, 2));
  try {
    const result = await runNpm(project, [
      'version',
      'minor',
      '--no-git-tag-version',
      '--foreground-scripts',
    ], { env: { LOG_FILE: log } });
    assert.equal(result.code, 0);
    const records = await readRecords(log);
    assert.deepEqual(records.map(({ event }) => event), [
      'preversion',
      'version',
      'postversion',
    ]);
    assert.ok(records.every(({ oldVersion }) => oldVersion === '1.2.3'));
    assert.ok(records.every(({ newVersion }) => newVersion === '1.3.0'));
    assert.deepEqual(records.map(({ packageVersion }) => packageVersion), [
      '1.2.3',
      '1.3.0',
      '1.3.0',
    ]);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
    // version 脚本若生成发布文件，应自行 git add；
    // npm 不会自动猜哪些产物应提交。
  },
);

test('脚本字符串交给平台 shell，复杂逻辑放入 Node 文件更可移植', async () => {
  const project = await createProject();
  await writeFile(join(project, 'portable.mjs'), `
    process.stdout.write(JSON.stringify({
      platform: process.platform,
      arguments: process.argv.slice(2),
    }));
  `);
  await writeFile(join(project, 'package.json'), JSON.stringify({
    name: 'portable-script-lesson',
    version: '1.0.0',
    private: true,
    scripts: {
      portable: 'node portable.mjs "value with spaces"',
    },
  }, null, 2));
  try {
    const result = await runNpm(project, ['run', '--silent', 'portable']);
    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.stdout), {
      platform: 'linux',
      arguments: ['value with spaces'],
    });
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // POSIX 默认 /bin/sh，Windows 默认 cmd.exe；
  // 管道、变量赋值和引号规则并不通用。
});
