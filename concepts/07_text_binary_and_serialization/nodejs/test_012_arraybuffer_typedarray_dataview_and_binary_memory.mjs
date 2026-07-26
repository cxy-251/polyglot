// polyglot-covers:
// - nodejs.language.arraybuffer-and-views
// - nodejs.language.typedarray-numeric-conversion
// - nodejs.language.typedarray-shared-memory-and-slicing
// - nodejs.language.dataview-endianness
// - nodejs.language.typedarray-method-semantics
// - nodejs.language.resizable-arraybuffer
// - nodejs.language.arraybuffer-transfer

import assert from 'node:assert/strict';
import test from 'node:test';

test('ArrayBuffer 是字节存储，TypedArray 是带元素类型的视图', () => {
  const buffer = new ArrayBuffer(8);
  const bytes = new Uint8Array(buffer);
  const words = new Uint16Array(buffer);

  bytes.set([1, 2, 3, 4]);

  assert.equal(buffer.byteLength, 8);
  assert.equal(bytes.length, 8);
  assert.equal(words.length, 4);
  assert.equal(ArrayBuffer.isView(bytes), true);
  assert.equal(ArrayBuffer.isView(new DataView(buffer)), true);
  assert.equal(ArrayBuffer.isView(buffer), false);

  // 多个视图共享同一内存。直接用多字节 TypedArray 解释结果会依赖主机字节序；需要稳定
  // 文件或协议格式时应使用 DataView 并明确 littleEndian 参数。
  assert.deepEqual([...bytes.slice(0, 4)], [1, 2, 3, 4]);
});

test('subarray 共享存储，slice 复制元素', () => {
  const original = Uint8Array.from([10, 20, 30, 40]);
  const shared = original.subarray(1, 3);
  const copied = original.slice(1, 3);

  shared[0] = 99;
  copied[1] = 88;

  assert.deepEqual([...original], [10, 99, 30, 40]);
  assert.deepEqual([...shared], [99, 30]);
  assert.deepEqual([...copied], [20, 88]);
  assert.equal(shared.buffer, original.buffer);
  assert.notEqual(copied.buffer, original.buffer);
});

test('整数 TypedArray 按位宽取模，Uint8ClampedArray 使用钳制舍入', () => {
  const bytes = Uint8Array.from([-1, 256, 257, 3.9]);
  assert.deepEqual([...bytes], [255, 0, 1, 3]);

  const clamped = Uint8ClampedArray.from([-1, 300, 1.5, 2.5, 3.5]);
  assert.deepEqual([...clamped], [0, 255, 2, 2, 4]);

  const signed = Int8Array.from([127, 128, 255]);
  assert.deepEqual([...signed], [127, -128, -1]);
});

test('BigInt TypedArray 只接受 BigInt 值', () => {
  const values = BigInt64Array.from([1n, -2n, 3n]);
  assert.deepEqual([...values], [1n, -2n, 3n]);

  assert.throws(() => {
    values[0] = 1;
  }, TypeError);

  const unsigned = BigUint64Array.of(-1n);
  assert.equal(unsigned[0], 2n ** 64n - 1n);
});

test('TypedArray sort 默认按数值排序且没有空槽', () => {
  const values = Uint8Array.from([20, 3, 100, 1]);
  values.sort();
  assert.deepEqual([...values], [1, 3, 20, 100]);

  assert.equal(Reflect.deleteProperty(values, '1'), false);
  assert.equal(values[1], 3);
  assert.equal(1 in values, true);

  // TypedArray 的索引集合固定；越界写入不会扩展 length，也不会创建普通索引属性。
  values[20] = 7;
  assert.equal(values.length, 4);
  assert.equal(20 in values, false);
});

test('TypedArray 方法通常返回同种视图，Array.from 才返回普通数组', () => {
  const values = Int16Array.from([1, 2, 3]);
  const mapped = values.map((value) => value * 2);
  const filtered = values.filter((value) => value > 1);

  assert.equal(mapped instanceof Int16Array, true);
  assert.deepEqual([...mapped], [2, 4, 6]);
  assert.equal(filtered instanceof Int16Array, true);
  assert.deepEqual([...filtered], [2, 3]);

  const ordinary = Array.from(values, (value) => value * 2);
  assert.equal(Array.isArray(ordinary), true);
  assert.deepEqual(ordinary, [2, 4, 6]);
});

test('DataView 可在非对齐偏移读写并显式选择字节序', () => {
  const buffer = new ArrayBuffer(8);
  const view = new DataView(buffer);

  view.setUint32(1, 0x01020304, false);
  assert.deepEqual([...new Uint8Array(buffer)], [0, 1, 2, 3, 4, 0, 0, 0]);
  assert.equal(view.getUint32(1, false), 0x01020304);
  assert.equal(view.getUint32(1, true), 0x04030201);

  view.setInt16(5, -2, true);
  assert.equal(view.getInt16(5, true), -2);
  assert.throws(() => view.getUint32(6), RangeError);
});

test('浮点视图保留 Infinity、负零和 NaN 语义', () => {
  const values = Float64Array.of(Infinity, -0, Number.NaN, 0.1 + 0.2);

  assert.equal(values[0], Infinity);
  assert.equal(Object.is(values[1], -0), true);
  assert.equal(Number.isNaN(values[2]), true);
  assert.equal(values[3], 0.30000000000000004);
});

test('可调整 ArrayBuffer 让长度跟踪视图与固定长度视图表现不同', {
  skip: typeof ArrayBuffer.prototype.resize !== 'function',
}, () => {
  const buffer = new ArrayBuffer(8, { maxByteLength: 16 });
  const tracking = new Uint8Array(buffer);
  const fixed = new Uint8Array(buffer, 0, 4);

  assert.equal(buffer.resizable, true);
  assert.equal(buffer.maxByteLength, 16);

  buffer.resize(12);
  assert.equal(tracking.length, 12);
  assert.equal(fixed.length, 4);

  buffer.resize(2);
  assert.equal(tracking.length, 2);
  assert.equal(fixed.length, 0);
  assert.throws(() => buffer.resize(17), RangeError);
});

test('transfer 转移所有权并分离原 ArrayBuffer', {
  skip: typeof ArrayBuffer.prototype.transfer !== 'function',
}, () => {
  const original = new ArrayBuffer(4);
  new Uint8Array(original).set([1, 2, 3, 4]);

  const moved = original.transfer(6);
  assert.equal(original.detached, true);
  assert.equal(original.byteLength, 0);
  assert.deepEqual([...new Uint8Array(moved)], [1, 2, 3, 4, 0, 0]);
  assert.throws(() => new Uint8Array(original), TypeError);
});
