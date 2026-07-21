// polyglot-covers:
// - nodejs.core.webassembly-validate-compile-instantiate-exports-and-custom-sections
// - nodejs.core.webassembly-streaming-compilation-mime-contract
// - nodejs.core.webassembly-compile-error-and-exported-function-call
// - nodejs.core.webassembly-memory-grow-buffer-detachment-and-shared-memory
// - nodejs.core.webassembly-table-externref-and-global-mutability
// - nodejs.core.wasi-experimental-status-version-and-import-object
// - nodejs.core.wasi-finalize-bindings-memory-and-single-initialization
// - nodejs.core.wasi-args-environment-and-preopen-capability-encoding
// - nodejs.core.wasi-start-command-proc-exit-return-code-and-single-start
// - nodejs.core.wasi-initialize-reactor-contract
// - nodejs.core.wasi-capabilities-are-not-a-secure-node-filesystem-sandbox

import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const experimentalWarnings = [];
const originalEmitWarning = process.emitWarning;
process.emitWarning = function captureExperimentalWarning(warning, options, ...args) {
  const type = typeof options === 'string' ? options : options?.type;
  if (type === 'ExperimentalWarning') {
    experimentalWarnings.push(String(warning));
    return;
  }
  return originalEmitWarning.call(this, warning, options, ...args);
};
const { WASI } = await import('node:wasi');
test.after(() => {
  process.emitWarning = originalEmitWarning;
});

const header = [0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00];

// (module (func (export "add") (param i32 i32) (result i32)
//   local.get 0 local.get 1 i32.add) (custom "meta" "*+"))
const addModuleBytes = new Uint8Array([
  ...header,
  0x01, 0x07, 0x01, 0x60, 0x02, 0x7f, 0x7f, 0x01, 0x7f,
  0x03, 0x02, 0x01, 0x00,
  0x07, 0x07, 0x01, 0x03, 0x61, 0x64, 0x64, 0x00, 0x00,
  0x0a, 0x09, 0x01, 0x07, 0x00, 0x20, 0x00, 0x20, 0x01, 0x6a, 0x0b,
  0x00, 0x07, 0x04, 0x6d, 0x65, 0x74, 0x61, 0x2a, 0x2b,
]);

function memoryAndFunctionModule(exportName, functionBody = [0x00, 0x0b]) {
  const name = [...Buffer.from(exportName)];
  const exportPayload = [
    0x02,
    0x06, ...Buffer.from('memory'), 0x02, 0x00,
    name.length, ...name, 0x00, 0x00,
  ];
  return new Uint8Array([
    ...header,
    0x01, 0x04, 0x01, 0x60, 0x00, 0x00,
    0x03, 0x02, 0x01, 0x00,
    0x05, 0x03, 0x01, 0x00, 0x01,
    0x07, exportPayload.length, ...exportPayload,
    0x0a, functionBody.length + 2, 0x01, functionBody.length, ...functionBody,
  ]);
}

const memoryOnlyBytes = new Uint8Array([
  ...header,
  0x05, 0x03, 0x01, 0x00, 0x01,
  0x07, 0x0a, 0x01, 0x06, ...Buffer.from('memory'), 0x02, 0x00,
]);

// 命令模块导入 proc_exit，并在 _start 中传入退出码 7。
const exitCommandBytes = new Uint8Array([
  ...header,
  0x01, 0x08,
  0x02,
  0x60, 0x01, 0x7f, 0x00,
  0x60, 0x00, 0x00,
  0x02, 0x24,
  0x01,
  0x16, ...Buffer.from('wasi_snapshot_preview1'),
  0x09, ...Buffer.from('proc_exit'),
  0x00, 0x00,
  0x03, 0x02, 0x01, 0x01,
  0x05, 0x03, 0x01, 0x00, 0x01,
  0x07, 0x13,
  0x02,
  0x06, ...Buffer.from('memory'), 0x02, 0x00,
  0x06, ...Buffer.from('_start'), 0x00, 0x01,
  0x0a, 0x08, 0x01, 0x06, 0x00, 0x41, 0x07, 0x10, 0x00, 0x0b,
]);

function decodeCString(bytes, offset) {
  let end = offset;
  while (bytes[end] !== 0) end += 1;
  return new TextDecoder().decode(bytes.subarray(offset, end));
}

test('WebAssembly 校验、编译、实例化并公开可检查的 imports/exports/custom sections', async () => {
  assert.equal(WebAssembly.validate(addModuleBytes), true);
  assert.equal(WebAssembly.validate(new Uint8Array([0, 1, 2])), false);

  const module = await WebAssembly.compile(addModuleBytes);
  assert.deepEqual(WebAssembly.Module.imports(module), []);
  assert.deepEqual(WebAssembly.Module.exports(module), [
    { name: 'add', kind: 'function' },
  ]);
  const custom = WebAssembly.Module.customSections(module, 'meta');
  assert.equal(custom.length, 1);
  assert.deepEqual([...new Uint8Array(custom[0])], [0x2a, 0x2b]);

  const instance = await WebAssembly.instantiate(module);
  assert.equal(instance.exports.add(20, 22), 42);
  await assert.rejects(WebAssembly.compile(new Uint8Array([0])), WebAssembly.CompileError);
});

test('compileStreaming 要求 application/wasm，响应体无需真实网络', async () => {
  const response = new Response(addModuleBytes, {
    headers: { 'content-type': 'application/wasm' },
  });
  const module = await WebAssembly.compileStreaming(Promise.resolve(response));
  assert.equal((await WebAssembly.instantiate(module)).exports.add(1, 2), 3);

  const wrongMime = new Response(addModuleBytes, {
    headers: { 'content-type': 'application/octet-stream' },
  });
  await assert.rejects(
    WebAssembly.compileStreaming(Promise.resolve(wrongMime)),
    TypeError,
  );
});

test('Memory.grow 替换普通 ArrayBuffer；shared memory 的旧视图仍指向原长度', () => {
  const memory = new WebAssembly.Memory({ initial: 1, maximum: 2 });
  const oldBuffer = memory.buffer;
  new Uint8Array(oldBuffer)[0] = 7;
  assert.equal(memory.grow(1), 1);
  assert.equal(oldBuffer.byteLength, 0);
  assert.equal(memory.buffer.byteLength, 2 * 65_536);
  assert.equal(new Uint8Array(memory.buffer)[0], 7);

  const shared = new WebAssembly.Memory({ initial: 1, maximum: 2, shared: true });
  const oldShared = shared.buffer;
  assert.ok(oldShared instanceof SharedArrayBuffer);
  assert.equal(shared.grow(1), 1);
  assert.equal(oldShared.byteLength, 65_536);
  assert.equal(shared.buffer.byteLength, 2 * 65_536);
  assert.notEqual(shared.buffer, oldShared);
});

test('Table 管理 externref 槽位，Global 用 mutable 决定能否从 JS 写值', () => {
  const first = { id: 1 };
  const second = { id: 2 };
  const table = new WebAssembly.Table({ element: 'externref', initial: 1, maximum: 2 }, first);
  assert.equal(table.get(0), first);
  assert.equal(table.grow(1, second), 1);
  assert.equal(table.length, 2);
  assert.equal(table.get(1), second);

  const mutable = new WebAssembly.Global({ value: 'i64', mutable: true }, 7n);
  mutable.value = 9n;
  assert.equal(mutable.value, 9n);
  const immutable = new WebAssembly.Global({ value: 'i32', mutable: false }, 3);
  assert.throws(() => {
    immutable.value = 4;
  }, TypeError);
});

test('WASI 要求明确版本，并按 preview1/unstable 返回不同导入命名空间', () => {
  assert.throws(() => new WASI(), /version/i);
  const preview = new WASI({ version: 'preview1' });
  const unstable = new WASI({ version: 'unstable' });

  assert.equal(preview.getImportObject().wasi_snapshot_preview1, preview.wasiImport);
  assert.equal(unstable.getImportObject().wasi_unstable, unstable.wasiImport);
  assert.ok(experimentalWarnings.some((warning) => /WASI/i.test(warning)));
});

test('finalizeBindings 绑定内存一次，随后可直接调用 WASI 参数与能力接口', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-wasi-preopen-'));
  try {
    const wasi = new WASI({
      version: 'preview1',
      args: ['app', '--flag'],
      env: { MODE: 'test' },
      preopens: { '/sandbox': directory },
    });
    const { instance } = await WebAssembly.instantiate(memoryOnlyBytes);
    wasi.finalizeBindings(instance);
    assert.throws(() => wasi.finalizeBindings(instance), /already started|initialized/i);

    const memory = new Uint8Array(instance.exports.memory.buffer);
    const view = new DataView(instance.exports.memory.buffer);
    assert.equal(wasi.wasiImport.args_sizes_get(0, 4), 0);
    assert.equal(view.getUint32(0, true), 2);
    assert.equal(view.getUint32(4, true), 11);
    assert.equal(wasi.wasiImport.args_get(8, 32), 0);
    assert.equal(decodeCString(memory, view.getUint32(8, true)), 'app');
    assert.equal(decodeCString(memory, view.getUint32(12, true)), '--flag');

    assert.equal(wasi.wasiImport.environ_sizes_get(0, 4), 0);
    assert.equal(view.getUint32(0, true), 1);
    assert.equal(view.getUint32(4, true), 10);
    assert.equal(wasi.wasiImport.environ_get(8, 32), 0);
    assert.equal(decodeCString(memory, view.getUint32(8, true)), 'MODE=test');

    assert.equal(wasi.wasiImport.fd_prestat_get(3, 0), 0);
    const guestNameLength = view.getUint32(4, true);
    assert.equal(wasi.wasiImport.fd_prestat_dir_name(3, 32, guestNameLength), 0);
    assert.equal(new TextDecoder().decode(memory.subarray(32, 32 + guestNameLength)), '/sandbox');
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
  // preopens 限定客体“看见什么”，但 Node 官方明确说明它目前不是可运行不可信代码的沙箱。
});

test('start 只接受导出 memory/_start 的命令模块，并把 proc_exit 转成返回码', async () => {
  const wasi = new WASI({ version: 'preview1', returnOnExit: true });
  const { instance } = await WebAssembly.instantiate(
    exitCommandBytes,
    wasi.getImportObject(),
  );
  assert.equal(wasi.start(instance), 7);
  assert.throws(() => wasi.start(instance), /already started/i);

  const { instance: wrongShape } = await WebAssembly.instantiate(
    memoryAndFunctionModule('_initialize'),
    new WASI({ version: 'preview1' }).getImportObject(),
  );
  const another = new WASI({ version: 'preview1' });
  assert.throws(() => another.start(wrongShape), /_start|_initialize/i);
});

test('initialize 只接受 reactor，可选调用 _initialize 且同一实例只能初始化一次', async () => {
  const wasi = new WASI({ version: 'preview1' });
  const { instance: reactor } = await WebAssembly.instantiate(
    memoryAndFunctionModule('_initialize'),
    wasi.getImportObject(),
  );
  assert.equal(wasi.initialize(reactor), undefined);
  assert.throws(() => wasi.initialize(reactor), /already started|initialized/i);

  const commandWasi = new WASI({ version: 'preview1' });
  const { instance: command } = await WebAssembly.instantiate(
    memoryAndFunctionModule('_start'),
    commandWasi.getImportObject(),
  );
  assert.throws(() => commandWasi.initialize(command), /_start/i);
});
