// polyglot-covers:
// - nodejs.core.process-version-release-platform-arch-and-features
// - nodejs.core.process-argv-exec-argv-exec-path-and-pids
// - nodejs.core.process-allowed-node-environment-flags
// - nodejs.core.process-get-builtin-module
// - nodejs.core.process-env-string-values-and-deletion
// - nodejs.core.process-load-env-file-and-existing-value-precedence
// - nodejs.core.process-cwd-and-chdir
// - nodejs.core.process-memory-available-and-constrained-memory
// - nodejs.core.process-cpu-and-resource-usage
// - nodejs.core.process-high-resolution-time
// - nodejs.core.process-active-resources-info
// - nodejs.core.process-kill-signal-zero

import assert from 'node:assert/strict';
import test from 'node:test';

import process, { loadEnvFile } from 'node:process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { isAbsolute, join } from 'node:path';
import { pathToFileURL } from 'node:url';

test('process 元数据描述当前 Node 构建、可执行文件与进程身份', () => {
  assert.equal(process.version, `v${process.versions.node}`);
  assert.equal(process.release.name, 'node');
  assert.equal(typeof process.release.lts, 'string');
  assert.equal(typeof process.platform, 'string');
  assert.equal(typeof process.arch, 'string');
  assert.equal(typeof process.features.inspector, 'boolean');
  assert.equal(typeof process.features.tls, 'boolean');
  assert.equal(isAbsolute(process.execPath), true);
  assert.ok(Array.isArray(process.argv));
  assert.ok(Array.isArray(process.execArgv));
  assert.ok(Number.isInteger(process.pid) && process.pid > 0);
  assert.ok(Number.isInteger(process.ppid) && process.ppid >= 0);
  assert.equal(typeof process.title, 'string');

  assert.ok(process.allowedNodeEnvironmentFlags.has('--trace-warnings'));
  // Set 会把下划线和部分 --flag=value 形式规范化，适合验证 NODE_OPTIONS 白名单。
  assert.equal(process.allowedNodeEnvironmentFlags.has('--trace_warnings'), true);
  assert.equal(process.allowedNodeEnvironmentFlags.has('--not-a-node-flag'), false);
});

test('getBuiltinModule 在任意模块系统中同步取得内置模块，不解析用户包', () => {
  const fs = process.getBuiltinModule('fs');
  const strictAssert = process.getBuiltinModule('assert/strict');

  assert.equal(typeof fs.readFile, 'function');
  assert.equal(strictAssert.equal, assert.equal);
  assert.equal(process.getBuiltinModule('definitely-not-a-builtin'), undefined);
  assert.ok(process.moduleLoadList.some((entry) => entry.includes('NativeModule')));
});

test('process.env 写入字符串并用 delete 删除，修改后必须恢复', () => {
  const key = 'POLYGLOT_PROCESS_ENV_VALUE';
  const previous = process.env[key];
  try {
    process.env[key] = '中文 value';
    assert.equal(process.env[key], '中文 value');
    assert.equal(Object.hasOwn(process.env, key), true);

    delete process.env[key];
    assert.equal(process.env[key], undefined);
  } finally {
    if (previous === undefined) delete process.env[key];
    else process.env[key] = previous;
  }
  // 不依赖非字符串的隐式转换；该行为已被弃用，并可能在未来直接报错。
});

test('loadEnvFile 解析 .env，且不会覆盖进程中已经存在的键', async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-process-'));
  const path = join(root, '.env');
  const loadedKey = 'POLYGLOT_LOADED_FROM_FILE';
  const existingKey = 'POLYGLOT_EXISTING_ENV';
  const previousLoaded = process.env[loadedKey];
  const previousExisting = process.env[existingKey];

  try {
    process.env[existingKey] = 'from process';
    await writeFile(path, [
      `${loadedKey}="quoted value"`,
      `${existingKey}=from file`,
      '# comment',
      '',
    ].join('\n'));
    assert.equal(loadEnvFile(pathToFileURL(path)), undefined);

    assert.equal(process.env[loadedKey], 'quoted value');
    assert.equal(process.env[existingKey], 'from process');
  } finally {
    if (previousLoaded === undefined) delete process.env[loadedKey];
    else process.env[loadedKey] = previousLoaded;
    if (previousExisting === undefined) delete process.env[existingKey];
    else process.env[existingKey] = previousExisting;
    await rm(root, { recursive: true, force: true });
  }
});

test('cwd/chdir 改变整个进程的相对路径基准，测试结束必须恢复', async () => {
  const previous = process.cwd();
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-cwd-'));
  try {
    assert.equal(process.chdir(root), undefined);
    assert.equal(process.cwd(), root);
    assert.equal(new URL('.', pathToFileURL(`${process.cwd()}/`)).pathname.endsWith('/'), true);
  } finally {
    process.chdir(previous);
    await rm(root, { recursive: true, force: true });
  }
  assert.equal(process.cwd(), previous);
});

test('memoryUsage、availableMemory 与 constrainedMemory 表达不同内存边界', () => {
  const usage = process.memoryUsage();
  assert.ok(usage.rss > 0);
  assert.ok(usage.heapTotal >= usage.heapUsed);
  assert.ok(usage.arrayBuffers >= 0);
  assert.ok(process.memoryUsage.rss() > 0);
  assert.ok(process.availableMemory() > 0);

  const constrained = process.constrainedMemory();
  assert.ok(constrained === undefined || constrained > 0);
  // rss 是本进程驻留集，availableMemory 是当前环境可用量，constrainedMemory
  // 是容器/资源限制上界；三者不能互相替代。
});

test('cpuUsage/resourceUsage 是累计指标，hrtime.bigint 适合计算短时差值', () => {
  const cpuBefore = process.cpuUsage();
  const timeBefore = process.hrtime.bigint();
  let checksum = 0;
  for (let index = 0; index < 10_000; index += 1) checksum += index;
  const elapsed = process.hrtime.bigint() - timeBefore;
  const delta = process.cpuUsage(cpuBefore);
  const resources = process.resourceUsage();

  assert.equal(checksum, 49_995_000);
  assert.ok(elapsed >= 0n);
  assert.ok(delta.user >= 0);
  assert.ok(delta.system >= 0);
  assert.ok(resources.userCPUTime >= 0);
  assert.ok(resources.systemCPUTime >= 0);
  assert.ok(resources.maxRSS > 0);
  assert.equal(typeof resources.voluntaryContextSwitches, 'number');
});

test('活动资源列表用于诊断事件循环，signal 0 只检查 PID 是否存在', () => {
  const resources = process.getActiveResourcesInfo();
  assert.ok(Array.isArray(resources));
  assert.ok(resources.every((name) => typeof name === 'string'));
  assert.equal(process.kill(process.pid, 0), true);

  assert.throws(
    () => process.kill(2 ** 31 - 1, 0),
    (error) => error.code === 'ESRCH',
  );
  // kill 名称容易误导：signal 0 不发送终止信号，只让内核执行存在性/权限检查。
});
