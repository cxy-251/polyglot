// polyglot-covers:
// - nodejs.core.process-report-get-report-header-stack-heap-libuv-and-resources
// - nodejs.core.process-report-error-context
// - nodejs.core.process-report-runtime-configuration-and-restoration
// - nodejs.core.process-report-exclude-environment-and-network
// - nodejs.core.process-report-write-report-directory-filename-return-and-stderr
// - nodejs.core.process-report-compact-json-workflow

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { promisify } from 'node:util';
import test from 'node:test';

const execFileAsync = promisify(execFile);

async function withTempDirectory(run) {
  const directory = await mkdtemp('/tmp/polyglot-nodejs-report-');
  try {
    return await run(directory);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test('getReport 返回当前进程的版本化快照，覆盖 JS、V8、libuv 和系统资源', () => {
  const report = process.report.getReport();
  assert.equal(report.header.nodejsVersion, process.version);
  assert.equal(report.header.processId, process.pid);
  assert.ok(Number.isInteger(report.header.reportVersion));
  assert.ok(report.header.reportVersion >= 1);
  assert.equal(report.header.event, 'JavaScript API');
  assert.ok(Array.isArray(report.header.commandLine));

  assert.match(report.javascriptStack.message, /ERR_SYNTHETIC.*JavaScript Callstack/);
  assert.ok(report.javascriptStack.stack.length > 0);
  assert.ok(report.javascriptStack.stack.every((line) => typeof line === 'string'));
  assert.ok(Array.isArray(report.nativeStack));
  assert.ok(report.javascriptHeap.totalMemory >= report.javascriptHeap.usedMemory);
  assert.equal(typeof report.javascriptHeap.heapSpaces, 'object');
  assert.ok(Object.keys(report.javascriptHeap.heapSpaces).length > 0);
  assert.ok(Array.isArray(report.libuv));
  assert.ok(report.libuv.some(({ type }) => type === 'loop'));
  assert.ok(report.resourceUsage.rss > 0);
  assert.ok(report.uvthreadResourceUsage.userCpuSeconds >= 0);
  assert.ok(report.userLimits.open_files.hard >= report.userLimits.open_files.soft);
  assert.ok(Array.isArray(report.sharedObjects));
  // 字段和 reportVersion 跨 LTS 一致；具体 native frame、句柄数量和内存值只能动态读取。
});

test('把原始 Error 交给 getReport，报告保留错误发生处而不是只显示处理处', () => {
  function createOriginalError() {
    return new Error('database connection failed');
  }

  const original = createOriginalError();
  const report = process.report.getReport(original);
  assert.equal(report.javascriptStack.message, 'Error: database connection failed');
  assert.ok(report.javascriptStack.stack.some((line) => line.includes('createOriginalError')));
  assert.equal(report.header.trigger, 'GetReport');
  // 在 catch 中生成报告时应传入捕获的 err，否则堆栈会指向 getReport 调用本身。
});

test('process.report 配置是进程级可变状态，修改后必须恢复', () => {
  const keys = [
    'compact',
    'directory',
    'excludeEnv',
    'excludeNetwork',
    'filename',
    'reportOnFatalError',
    'reportOnSignal',
    'reportOnUncaughtException',
    'signal',
  ];
  const original = Object.fromEntries(keys.map((key) => [key, process.report[key]]));

  try {
    process.report.compact = true;
    process.report.directory = '/tmp';
    process.report.excludeEnv = true;
    process.report.excludeNetwork = true;
    process.report.filename = 'polyglot-report.json';
    process.report.reportOnFatalError = false;
    process.report.reportOnSignal = false;
    process.report.reportOnUncaughtException = false;

    assert.equal(process.report.compact, true);
    assert.equal(process.report.directory, '/tmp');
    assert.equal(process.report.excludeEnv, true);
    assert.equal(process.report.excludeNetwork, true);
    assert.equal(process.report.filename, 'polyglot-report.json');
    assert.equal(typeof process.report.signal, 'string');
  } finally {
    for (const [key, value] of Object.entries(original)) {
      process.report[key] = value;
    }
  }

  for (const [key, value] of Object.entries(original)) {
    assert.equal(process.report[key], value);
  }
});

test('excludeEnv/excludeNetwork 同时保护环境变量和网络接口等敏感诊断信息', () => {
  const originalExcludeEnv = process.report.excludeEnv;
  const originalExcludeNetwork = process.report.excludeNetwork;
  try {
    process.report.excludeEnv = true;
    process.report.excludeNetwork = true;
    const report = process.report.getReport();
    assert.equal('environmentVariables' in report, false);
    assert.equal('networkInterfaces' in report.header, false);
    assert.ok(report.libuv.every((handle) => {
      return handle.localEndpoint?.host === undefined
        && handle.remoteEndpoint?.host === undefined;
    }));
  } finally {
    process.report.excludeEnv = originalExcludeEnv;
    process.report.excludeNetwork = originalExcludeNetwork;
  }
  // 报告可能进入工单或日志系统；默认环境变量常含密钥，生产环境应先决定脱敏策略。
});

test('writeReport 在指定目录写紧凑 JSON、返回文件名，并把进度写到 stderr', async () => {
  await withTempDirectory(async (directory) => {
    const script = `
      process.report.directory = ${JSON.stringify(directory)};
      process.report.compact = true;
      process.report.excludeEnv = true;
      process.report.excludeNetwork = true;
      const filename = process.report.writeReport(
        'manual-report.json',
        new Error('worker failed'),
      );
      process.stdout.write(filename);
    `;
    const { stdout, stderr } = await execFileAsync(
      process.execPath,
      ['--input-type=module', '--eval', script],
      { env: process.env },
    );

    assert.equal(stdout, 'manual-report.json');
    assert.match(stderr, /Writing Node\.js report to file/);
    assert.match(stderr, /Node\.js report completed/);

    const text = await readFile(`${directory}/manual-report.json`, 'utf8');
    assert.equal(text.trim().split('\n').length, 1);
    const report = JSON.parse(text);
    assert.equal(report.javascriptStack.message, 'Error: worker failed');
    assert.equal(report.header.filename, 'manual-report.json');
    assert.equal('environmentVariables' in report, false);
    assert.equal('networkInterfaces' in report.header, false);
  });
  // compact 只改变文件排版；writeReport 仍同步暂停目标线程来收集状态，不适合高频调用。
});
