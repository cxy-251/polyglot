// polyglot-covers:
// - nodejs.core.v8-heap-code-space-and-cpp-statistics
// - nodejs.core.v8-cached-data-version-tag
// - nodejs.core.v8-serialize-deserialize-structured-clone-graph-and-builtins
// - nodejs.core.v8-serialization-unsupported-functions-and-prototype-loss
// - nodejs.core.v8-default-serializer-primitives-and-wire-format
// - nodejs.core.v8-serializer-out-of-band-array-buffer-transfer
// - nodejs.core.v8-query-objects-count-summary-and-prototype-chain
// - nodejs.core.v8-query-objects-node24-experimental-warning
// - nodejs.core.v8-promise-hooks-lifecycle-parent-and-stop
// - nodejs.core.v8-startup-snapshot-mode-detection
// - nodejs.core.v8-gc-profiler-lifecycle
// - nodejs.core.v8-sync-cpu-profile-handle-and-json-profile
// - nodejs.core.v8-string-one-byte-representation

import assert from 'node:assert/strict';
import test from 'node:test';
import {
  cachedDataVersionTag,
  DefaultDeserializer,
  DefaultSerializer,
  deserialize,
  GCProfiler,
  getCppHeapStatistics,
  getHeapCodeStatistics,
  getHeapSpaceStatistics,
  getHeapStatistics,
  isStringOneByteRepresentation,
  promiseHooks,
  queryObjects,
  serialize,
  startCpuProfile,
  startupSnapshot,
} from 'node:v8';

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
test.after(() => {
  process.emitWarning = originalEmitWarning;
});

test('堆统计分别回答总量、空间和编译代码占用，字段集合不等同', () => {
  const heap = getHeapStatistics();
  assert.ok(heap.total_heap_size >= heap.used_heap_size);
  assert.ok(heap.heap_size_limit >= heap.total_heap_size);
  assert.ok(heap.external_memory >= 0);
  assert.ok(heap.number_of_native_contexts >= 1);

  const spaces = getHeapSpaceStatistics();
  assert.ok(spaces.length > 0);
  assert.ok(spaces.every((space) => typeof space.space_name === 'string'));
  assert.ok(spaces.every((space) => space.space_used_size >= 0));
  assert.ok(spaces.some((space) => space.space_name.includes('old_space')));

  const code = getHeapCodeStatistics();
  assert.ok(code.code_and_metadata_size > 0);
  assert.ok(code.bytecode_and_metadata_size >= 0);
  assert.ok(code.external_script_source_size >= 0);

  const cppHeap = getCppHeapStatistics('brief');
  assert.equal(cppHeap.detail_level, 'brief');
  assert.ok(cppHeap.committed_size_bytes >= cppHeap.used_size_bytes);
  assert.deepEqual(cppHeap.space_statistics, []);
  // 空间名称、顺序和可用空间都由 V8 版本决定；监控代码应看字段而不是固定数组下标。
});

test('cachedDataVersionTag 是当前 V8、启动 flags 与 CPU 能力共同决定的无符号标签', () => {
  const first = cachedDataVersionTag();
  const second = cachedDataVersionTag();
  assert.equal(first, second);
  assert.equal(Number.isInteger(first), true);
  assert.ok(first >= 0 && first <= 0xffff_ffff);
  // 标签相同只表示 vm.Script cachedData 兼容；它不是 Node 版本号或内容哈希。
});

test('serialize/deserialize 保留循环、共享引用和结构化克隆支持的内置类型', () => {
  const shared = { answer: 42 };
  const source = {
    bigint: 2n ** 70n,
    date: new Date('2026-01-02T03:04:05.000Z'),
    map: new Map([['key', shared]]),
    regexp: /node/giu,
    set: new Set(['a', 'b']),
    typed: new Uint16Array([1, 65_535]),
    first: shared,
    second: shared,
  };
  source.self = source;

  const bytes = serialize(source);
  const clone = deserialize(bytes);
  assert.ok(Buffer.isBuffer(bytes));
  assert.notEqual(clone, source);
  assert.equal(clone.self, clone);
  assert.equal(clone.first, clone.second);
  assert.equal(clone.map.get('key'), clone.first);
  assert.deepEqual(clone.date, source.date);
  assert.deepEqual(clone.regexp, source.regexp);
  assert.deepEqual(clone.set, source.set);
  assert.deepEqual(clone.typed, source.typed);
  assert.equal(clone.bigint, source.bigint);
  // 格式向后兼容，但同值不保证产生逐字节相同的 Buffer，不能拿它代替规范化编码。
});

test('序列化拒绝函数，并把普通类实例还原为只有可枚举数据的普通对象', () => {
  class Job {
    constructor(id) {
      this.id = id;
    }

    run() {
      return this.id;
    }
  }

  const clone = deserialize(serialize(new Job(7)));
  assert.deepEqual(clone, { id: 7 });
  assert.equal(clone instanceof Job, false);
  assert.equal('run' in clone, false);
  assert.throws(() => serialize({ callback() {} }), Error);
  // structured clone 传数据而不传行为；反序列化后若需类语义，应用必须显式重建实例。
});

test('DefaultSerializer 可混合写入线格式头、原始数值/字节和普通 JS 值', () => {
  const serializer = new DefaultSerializer();
  serializer.writeHeader();
  serializer.writeUint32(0xffff_ffff);
  serializer.writeUint64(0x1234_5678, 0x90ab_cdef);
  serializer.writeDouble(Math.PI);
  serializer.writeRawBytes(Uint8Array.of(0xde, 0xad));
  serializer.writeValue({ ready: true });
  const bytes = serializer.releaseBuffer();

  const deserializer = new DefaultDeserializer(bytes);
  assert.equal(deserializer.readHeader(), true);
  assert.ok(deserializer.getWireFormatVersion() > 0);
  assert.equal(deserializer.readUint32(), 0xffff_ffff);
  assert.deepEqual(deserializer.readUint64(), [0x1234_5678, 0x90ab_cdef]);
  assert.equal(deserializer.readDouble(), Math.PI);
  assert.deepEqual([...deserializer.readRawBytes(2)], [0xde, 0xad]);
  assert.deepEqual(deserializer.readValue(), { ready: true });
  // releaseBuffer 后继续使用 serializer 是未定义行为；协议也必须自己记录 raw bytes 长度。
});

test('transferArrayBuffer 只在序列化流中登记 ID，真实内存由接收方另行提供', () => {
  const sourceBuffer = Uint8Array.of(1, 2, 3, 4).buffer;
  const serializer = new DefaultSerializer();
  serializer.writeHeader();
  serializer.transferArrayBuffer(17, sourceBuffer);
  serializer.writeValue({ payload: sourceBuffer });
  const bytes = serializer.releaseBuffer();

  const targetBuffer = Uint8Array.of(9, 8, 7, 6).buffer;
  const deserializer = new DefaultDeserializer(bytes);
  deserializer.readHeader();
  deserializer.transferArrayBuffer(17, targetBuffer);
  const decoded = deserializer.readValue();

  assert.equal(decoded.payload, targetBuffer);
  assert.deepEqual([...new Uint8Array(decoded.payload)], [9, 8, 7, 6]);
  assert.equal(sourceBuffer.byteLength, 4);
  // 此 API 不像 structuredClone 的 transfer list 那样分离源缓冲区；它是带外协议的 ID 映射。
});

test('queryObjects 按原型链计数且只返回数量或摘要，不泄漏堆中对象引用', () => {
  class Record {
    constructor(id) {
      this.id = id;
    }
  }
  class DetailedRecord extends Record {
    constructor(id) {
      super(id);
      this.kind = 'detail';
    }
  }

  const retained = [new Record(1), new DetailedRecord(2)];
  const recordCount = queryObjects(Record);
  const detailedCount = queryObjects(DetailedRecord, { format: 'count' });
  const summaries = queryObjects(DetailedRecord, { format: 'summary' });
  assert.ok(recordCount >= retained.length);
  assert.ok(detailedCount >= 1);
  assert.ok(summaries.length >= 1);
  assert.ok(summaries.every((summary) => typeof summary === 'string'));
  assert.ok(summaries.some((summary) => summary.includes('DetailedRecord')));
  assert.equal(retained[1].kind, 'detail');
  assert.ok(experimentalWarnings.some((warning) => warning.includes('queryObjects')));
  // 子类实例的原型链包含父类；因此父类查询还会计入子类原型等对象，不应断言精确数量。
  // Node 24.18 文档已标为 stable，但实现仍发 ExperimentalWarning，升级后应重新核对这一差异。
});

test('promiseHooks 关联 continuation 与 parent，并在停用函数调用后停止观察', async () => {
  let root;
  const parents = new WeakMap();
  const lifecycle = new WeakMap();
  const counts = { init: 0, before: 0, after: 0, settled: 0 };
  const record = (promise, event) => {
    counts[event] += 1;
    const events = lifecycle.get(promise) ?? [];
    events.push(event);
    lifecycle.set(promise, events);
  };
  const stop = promiseHooks.createHook({
    init(promise, parent) {
      parents.set(promise, parent);
      record(promise, 'init');
    },
    before(promise) {
      record(promise, 'before');
    },
    after(promise) {
      record(promise, 'after');
    },
    settled(promise) {
      record(promise, 'settled');
    },
  });

  root = Promise.resolve(20);
  const child = root.then((value) => value + 22);
  assert.equal(parents.get(child), root);
  assert.equal(await child, 42);
  await Promise.resolve();
  stop();
  assert.ok(lifecycle.get(child).includes('settled'));
  assert.ok(counts.init >= 2);
  assert.ok(counts.before >= 1);
  assert.ok(counts.after >= 1);
  assert.ok(counts.settled >= 2);

  const countsAfterStop = { ...counts };
  const unobserved = Promise.resolve('unobserved').then((value) => value);
  await unobserved;
  assert.equal(lifecycle.has(unobserved), false);
  assert.deepEqual(counts, countsAfterStop);
  assert.throws(() => promiseHooks.onInit(async () => {}), TypeError);
  // hook 回调必须是同步普通函数；async 回调会创建新 Promise，导致无限递归。
});

test('startupSnapshot 在普通测试进程中只做能力探测，不注册仅构建阶段可用的回调', () => {
  assert.equal(Boolean(startupSnapshot.isBuildingSnapshot()), false);
  assert.throws(
    () => startupSnapshot.addSerializeCallback(() => {}),
    { code: 'ERR_NOT_BUILDING_SNAPSHOT' },
  );
});

test('GCProfiler 的 stop 返回本线程采集窗口，即使窗口内没有恰好发生 GC', () => {
  const profiler = new GCProfiler();
  profiler.start();
  const retained = Array.from({ length: 100 }, (_, index) => ({ index }));
  const report = profiler.stop();

  assert.equal(report.version, 1);
  assert.ok(report.endTime >= report.startTime);
  assert.ok(Array.isArray(report.statistics));
  assert.equal(retained.length, 100);
  // statistics 可以为空：GC 调度由 V8 决定，教学测试不靠强制 GC 或内存压力制造事件。
});

test('startCpuProfile 返回句柄，stop 产出可交给 DevTools 的 CPU Profile JSON', () => {
  const handle = startCpuProfile();
  let checksum = 0;
  for (let index = 0; index < 20_000; index += 1) {
    checksum = (checksum + index) % 65_521;
  }
  const profile = JSON.parse(handle.stop());

  assert.ok(Array.isArray(profile.nodes));
  assert.ok(profile.nodes.length > 0);
  assert.ok(profile.endTime >= profile.startTime);
  assert.ok(Array.isArray(profile.samples));
  assert.ok(Array.isArray(profile.timeDeltas));
  assert.ok(checksum >= 0);
});

test('isStringOneByteRepresentation 查询 V8 当前存储形式，不等价于字符范围检测', () => {
  assert.equal(isStringOneByteRepresentation('plain ASCII'), true);
  assert.equal(isStringOneByteRepresentation('中文'), false);
  assert.throws(() => isStringOneByteRepresentation(new String('boxed')), TypeError);
  // 返回 false 只说明当前是 UTF-16 表示；某些纯 Latin-1 字符串也可能因构造过程而使用 UTF-16。
});
