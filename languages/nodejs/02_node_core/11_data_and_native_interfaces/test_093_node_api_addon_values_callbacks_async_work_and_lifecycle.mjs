// polyglot-covers:
// - nodejs.core.node-api-direct-shared-library-build-and-node-extension-loading
// - nodejs.core.node-api-runtime-abi-version-and-context-aware-module-init
// - nodejs.core.node-api-javascript-primitive-value-creation
// - nodejs.core.node-api-callback-info-arguments-this-and-native-function-call
// - nodejs.core.node-api-buffer-mutation-and-typed-array-arraybuffer-metadata
// - nodejs.core.node-api-native-error-code-message-and-javascript-throw
// - nodejs.core.node-api-define-class-wrap-unwrap-accessor-and-finalizer
// - nodejs.core.node-api-promise-deferred-async-work-execute-and-complete
// - nodejs.core.node-api-addon-worker-thread-multiple-environments
// - nodejs.core.node-api-temporary-build-output-and-header-discovery

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Worker } from 'node:worker_threads';

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const buildDirectory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-node-api-'));
const addonPath = join(buildDirectory, 'learning-addon.node');
const includeDirectory = join(dirname(dirname(process.execPath)), 'include', 'node');
const sourcePath = fileURLToPath(
  new URL('./fixtures/node_api_learning_addon.c', import.meta.url),
);
const compiler = process.env.CC || 'cc';
const compilation = spawnSync(
  compiler,
  [
    '-std=c11',
    '-shared',
    '-fPIC',
    '-Wall',
    '-Wextra',
    '-Werror',
    '-I',
    includeDirectory,
    sourcePath,
    '-o',
    addonPath,
  ],
  { encoding: 'utf8' },
);
if (compilation.status !== 0) {
  throw new Error(`Node-API fixture compilation failed:\n${compilation.stderr}`);
}
const addon = require(addonPath);

test.after(() => {
  rmSync(buildDirectory, { recursive: true, force: true });
});

test('二进制扩展从 Node 发行版头文件直接构建，并报告运行时 Node-API ABI', () => {
  assert.equal(existsSync(addonPath), true);
  assert.ok(Number.isInteger(addon.runtimeNapiVersion));
  assert.equal(addon.runtimeNapiVersion, Number(process.versions.napi));
  // Node-API 的版本号是 ABI 能力级别，不等同于 Node 主版本，也不等同于插件包版本。
});

test('原生代码创建的 JavaScript primitive 保持各自语言类型与精度', () => {
  const values = addon.createValues();
  assert.equal(values.undefinedValue, undefined);
  assert.equal(values.nullValue, null);
  assert.equal(values.booleanValue, true);
  assert.equal(values.numberValue, 1.25);
  assert.equal(values.bigintValue, 9_007_199_254_740_993n);
  assert.equal(values.stringValue, 'native text');
  assert.equal(typeof values.symbolValue, 'symbol');
  assert.equal(values.symbolValue.description, 'native-symbol');
});

test('napi_get_cb_info 同时取得实参和 this，napi_call_function 可回调 JavaScript', () => {
  const receiver = { name: 'receiver' };
  assert.deepEqual(addon.inspectCall.call(receiver, receiver, 2, 3.5), {
    argc: 3,
    sameReceiver: true,
    sum: 5.5,
  });
  assert.equal(addon.callWith((value) => value * 3, 7), 21);
  assert.throws(() => addon.callWith(), /callback and value are required/);
  // C 侧先声明 argc 容量；多余实参会被截断，因此接口应显式设计最大参数数或逐项校验。
});

test('Buffer 暴露同一块可变内存，TypedArray 还包含视图偏移和底层缓冲区长度', () => {
  const buffer = Buffer.from([1, 2, 3, 4]);
  assert.equal(addon.reverseBufferEdges(buffer), 4);
  assert.deepEqual([...buffer], [4, 2, 3, 1]);
  const bytes = new Uint8Array([5, 6]);
  assert.equal(addon.reverseBufferEdges(bytes), 2);
  assert.deepEqual([...bytes], [6, 5]);
  const dataView = new DataView(new ArrayBuffer(2));
  dataView.setUint8(0, 7);
  dataView.setUint8(1, 8);
  assert.equal(addon.reverseBufferEdges(dataView), 2);
  assert.deepEqual([dataView.getUint8(0), dataView.getUint8(1)], [8, 7]);
  assert.throws(() => addon.reverseBufferEdges({}), /Buffer required/);
  // Node 24 的 napi_is_buffer/get_buffer_info 接受连续字节视图，不只接受 Buffer 子类。

  const arrayBuffer = new ArrayBuffer(16);
  const typed = new Uint16Array(arrayBuffer, 4, 3);
  const info = addon.typedArrayInfo(typed);
  assert.equal(info.length, 3);
  assert.equal(info.byteOffset, 4);
  assert.equal(info.bufferByteLength, 16);
  assert.equal(Number.isInteger(info.type), true);
});

test('napi_throw 把原生 Error 的 code 和 message 原样交给 JavaScript 异常机制', () => {
  assert.throws(() => addon.throwCode(), {
    name: 'Error',
    code: 'ERR_NATIVE_EXAMPLE',
    message: 'native failure',
  });
});

test('define_class 配合 wrap/unwrap 保存原生实例状态，并用 accessor 暴露只读值', () => {
  const counter = new addon.Counter(10);
  assert.equal(counter.value, 10);
  assert.equal(counter.increment(), 11);
  assert.equal(counter.value, 11);
  assert.equal(counter instanceof addon.Counter, true);
  assert.throws(() => {
    counter.value = 100;
  }, TypeError);
  // 原生内存由 napi_wrap 的 finalizer 释放；业务 API 不应要求用户手动 free 指针。
});

test('async work 在线程池执行，再在事件循环 complete 回调中落定 Promise', async () => {
  const promise = addon.doubleAsync(21);
  assert.ok(promise instanceof Promise);
  assert.equal(await promise, 42);
  await assert.rejects(
    Promise.resolve().then(() => addon.doubleAsync('not a number')),
    { message: 'A number was expected' },
  );
  // napi_status 只描述失败种类；这里的统一检查宏选择抛 Error，API 可另行映射成 TypeError。
});

test('NAPI_MODULE_INIT 是 context-aware 注册入口，同一插件可在 worker 环境重新初始化', async () => {
  const code = String.raw`
const { parentPort, workerData } = require('node:worker_threads');
const addon = require(workerData);
const counter = new addon.Counter(4);
parentPort.postMessage({
  value: counter.increment(),
  napi: addon.runtimeNapiVersion,
});
`;
  const worker = new Worker(code, { eval: true, workerData: addonPath });
  const result = await new Promise((resolve, reject) => {
    worker.once('message', resolve);
    worker.once('error', reject);
  });
  assert.deepEqual(result, {
    value: 5,
    napi: Number(process.versions.napi),
  });
  assert.equal(await worker[Symbol.asyncDispose](), undefined);
});
