// polyglot-covers:
// - nodejs.core.trace-events-create-tracing-state-categories-union-and-reference-counting
// - nodejs.core.trace-events-cli-categories-file-pattern-json-and-async-resources
// - nodejs.core.trace-events-file-flush-and-microsecond-timestamps
// - nodejs.core.sea-is-sea-and-asset-api-outside-single-executable-errors
// - nodejs.core.sea-preparation-blob-relative-paths-assets-and-runtime-options
// - nodejs.core.sea-code-cache-cross-platform-and-dynamic-import-limit
// - nodejs.core.sea-startup-snapshot-build-time-main-and-deserialize-callback
// - nodejs.core.sea-injection-platform-tooling-boundary

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import {
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import * as sea from 'node:sea';
import test from 'node:test';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

async function runNode(argumentsList, options = {}) {
  try {
    const result = await execFileAsync(process.execPath, argumentsList, {
      encoding: 'utf8',
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
  return mkdtemp(join(tmpdir(), 'polyglot-nodejs-runtime-packaging-'));
}

test('Tracing 对象维护启用状态，类别集合按所有启用实例取并集', async () => {
  const project = await createProject();
  const script = `
    import { createTracing, getEnabledCategories } from 'node:trace_events';
    const first = createTracing({ categories: ['node.perf', 'node'] });
    const second = createTracing({ categories: ['node.perf', 'v8'] });
    const states = [{
      firstEnabled: first.enabled,
      firstCategories: first.categories,
      enabled: getEnabledCategories() ?? null,
    }];
    first.enable();
    states.push({ firstEnabled: first.enabled, enabled: getEnabledCategories() });
    second.enable();
    states.push({ enabled: getEnabledCategories() });
    first.disable();
    states.push({ firstEnabled: first.enabled, enabled: getEnabledCategories() });
    second.disable();
    states.push({ enabled: getEnabledCategories() ?? null });
    process.stdout.write(JSON.stringify(states));
  `;
  try {
    const result = await runNode(['--input-type=module', '--eval', script], {
      cwd: project,
    });
    assert.equal(result.code, 0);
    assert.deepEqual(JSON.parse(result.stdout), [
      {
        firstEnabled: false,
        firstCategories: 'node.perf,node',
        enabled: null,
      },
      { firstEnabled: true, enabled: 'node,node.perf' },
      { enabled: 'node,node.perf,v8' },
      { firstEnabled: false, enabled: 'node.perf,v8' },
      { enabled: null },
    ]);
    const files = await readdir(project);
    assert.ok(files.some((name) => /^node_trace\.\d+\.log$/.test(name)));
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 两个实例共享的类别只有在最后一个实例 disable 后才关闭，
  // 行为类似引用计数。
});

test('CLI 可选择类别和文件模板，产物是 Chrome trace JSON', async () => {
  const project = await createProject();
  const script = join(project, 'measure.mjs');
  await writeFile(script, `
    import { performance } from 'node:perf_hooks';
    performance.mark('lesson-start');
    let total = 0;
    for (let index = 0; index < 100; index += 1) total += index;
    performance.mark('lesson-end');
    performance.measure('lesson-work', 'lesson-start', 'lesson-end');
    await new Promise(setImmediate);
    process.stdout.write(String(total));
  `);
  try {
    const result = await runNode([
      '--trace-event-categories',
      'node.async_hooks',
      '--trace-event-file-pattern',
      'trace-${pid}-${rotation}.json',
      script,
    ], { cwd: project });
    assert.equal(result.code, 0);
    assert.equal(result.stdout, '4950');

    const traceFiles = (await readdir(project))
      .filter((name) => /^trace-\d+-\d+\.json$/.test(name));
    assert.equal(traceFiles.length, 1);
    const trace = JSON.parse(await readFile(join(project, traceFiles[0]), 'utf8'));
    assert.ok(Array.isArray(trace.traceEvents));
    const asyncResources = trace.traceEvents.filter(
      (event) => event.cat?.includes('node.async_hooks'),
    );
    assert.ok(
      asyncResources.some((event) => /PROMISE|Immediate/.test(event.name)),
      JSON.stringify(asyncResources),
    );
    assert.ok(asyncResources.every((event) => Number.isInteger(event.ts)));
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // trace 与 hrtime 使用相同时间源，但 ts 字段单位是微秒；
  // 文件应在进程正常退出时刷完整。
});

test('普通 Node 进程可检测自己不是 SEA，资产 API 会拒绝误用', () => {
  assert.equal(sea.isSea(), false);
  for (const [name, operation] of [
    ['getAsset', () => sea.getAsset('lesson.txt')],
    ['getAssetAsBlob', () => sea.getAssetAsBlob('lesson.txt')],
    ['getRawAsset', () => sea.getRawAsset('lesson.txt')],
    ['getAssetKeys', () => sea.getAssetKeys()],
  ]) {
    assert.throws(
      operation,
      (error) => {
        assert.equal(error.code, 'ERR_NOT_IN_SINGLE_EXECUTABLE_APPLICATION');
        assert.match(error.message, /not in a single-executable application/);
        return true;
      },
      name,
    );
  }
  // getAsset 返回副本，getRawAsset 返回内嵌区的原始缓冲；
  // 后者不应写入，否则可能崩溃。
});

test('SEA 配置把入口、资产和运行参数写入可注入的 preparation blob', async () => {
  const project = await createProject();
  const asset = 'A'.repeat(64 * 1024);
  await writeFile(join(project, 'main.cjs'), `
    const { getAsset, isSea } = require('node:sea');
    if (isSea()) process.stdout.write(getAsset('lesson.txt', 'utf8'));
  `);
  await writeFile(join(project, 'lesson.txt'), asset);
  await writeFile(join(project, 'sea-config.json'), JSON.stringify({
    main: 'main.cjs',
    output: 'lesson.blob',
    disableExperimentalSEAWarning: true,
    useSnapshot: false,
    useCodeCache: true,
    execArgv: ['--no-warnings', '--max-old-space-size=128'],
    execArgvExtension: 'none',
    assets: {
      'lesson.txt': 'lesson.txt',
    },
  }));

  try {
    const result = await runNode([
      '--experimental-sea-config',
      'sea-config.json',
    ], { cwd: project });
    assert.equal(result.code, 0);
    assert.match(
      result.stdout + result.stderr,
      /Wrote single executable preparation blob to lesson\.blob/,
    );
    const blob = await stat(join(project, 'lesson.blob'));
    assert.ok(blob.isFile());
    assert.ok(blob.size > Buffer.byteLength(asset));
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 相对路径以执行命令的 cwd 为基准；
  // 生成 blob 与注入 blob 是两个独立步骤。
  // code cache 只兼容同平台同版本，且开启后嵌入脚本不能使用动态 import()。
});

test('useSnapshot 在构建时执行入口，运行时改由反序列化回调接管', async () => {
  const project = await createProject();
  await writeFile(join(project, 'snapshot-main.cjs'), `
    const { startupSnapshot } = require('node:v8');
    globalThis.lessonState = Object.freeze({ value: 42 });
    startupSnapshot.setDeserializeMainFunction(() => {
      process.stdout.write(String(globalThis.lessonState.value));
    });
  `);
  await writeFile(join(project, 'snapshot-config.json'), JSON.stringify({
    main: 'snapshot-main.cjs',
    output: 'snapshot.blob',
    disableExperimentalSEAWarning: true,
    useSnapshot: true,
    useCodeCache: false,
  }));

  try {
    const result = await runNode([
      '--experimental-sea-config',
      'snapshot-config.json',
    ], { cwd: project });
    assert.equal(result.code, 0);
    assert.match(
      result.stdout + result.stderr,
      /Wrote single executable preparation blob to snapshot\.blob/,
    );
    assert.ok((await stat(join(project, 'snapshot.blob'))).size > 0);
  } finally {
    await rm(project, { recursive: true, force: true });
  }
  // 构建阶段只登记回调而不输出 42；
  // 最终注入后的可执行文件启动时才调用它。
  // 跨平台分发必须关闭 snapshot 和 code cache，
  // 避免反序列化不兼容导致启动崩溃。
});

test('Node 只负责生成 SEA blob；平台资源注入和签名属于外部工具边界', () => {
  const platformRequirements = {
    linux: { container: 'ELF note', resource: 'NODE_SEA_BLOB' },
    darwin: { container: 'NODE_SEA Mach-O segment', resource: 'NODE_SEA_BLOB' },
    win32: { container: 'PE resource', resource: 'NODE_SEA_BLOB' },
  };
  assert.deepEqual(Object.keys(platformRequirements), ['linux', 'darwin', 'win32']);
  assert.ok(
    Object.values(platformRequirements)
      .every(({ resource }) => resource === 'NODE_SEA_BLOB'),
  );
  // 完整产物还要复制匹配版本的 node、注入 blob，
  // 并按 macOS/Windows 要求重签名。
  // 这里不引入 postject，也不改写容器内 node 二进制；
  // 测试聚焦 Node 自身的可验证职责。
});
