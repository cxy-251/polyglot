// polyglot-covers:
// - nodejs.core.buffer-alloc-alloc-unsafe-and-from
// - nodejs.core.buffer-string-encodings-and-byte-length
// - nodejs.core.buffer-arraybuffer-sharing-and-copying
// - nodejs.core.buffer-slice-subarray-and-copy
// - nodejs.core.buffer-integer-float-and-bigint-io
// - nodejs.core.buffer-search-compare-concat-and-swap
// - nodejs.core.buffer-json-and-inspection

import assert from 'node:assert/strict';
import test from 'node:test';

import { Buffer } from 'node:buffer';

test('Buffer 是 Uint8Array 子类，alloc 默认清零', () => {
  const buffer = Buffer.alloc(4);

  assert.equal(buffer instanceof Buffer, true);
  assert.equal(buffer instanceof Uint8Array, true);
  assert.equal(Buffer.isBuffer(buffer), true);
  assert.equal(Buffer.isBuffer(new Uint8Array(4)), false);
  assert.deepEqual([...buffer], [0, 0, 0, 0]);

  buffer.fill(0xaa, 1, 3);
  assert.deepEqual([...buffer], [0, 0xaa, 0xaa, 0]);
});

test('allocUnsafe 省略初始化成本，读取前必须完整覆盖内容', () => {
  const buffer = Buffer.allocUnsafe(8);

  // 不能断言初始字节：它们可能来自复用内存。案例立即 fill，避免泄漏先前进程数据。
  buffer.fill(0);
  buffer.writeUInt32BE(0x01020304, 0);
  buffer.writeUInt32BE(0x05060708, 4);
  assert.equal(buffer.toString('hex'), '0102030405060708');

  assert.throws(() => Buffer.alloc(-1), RangeError);
});

test('字符串 length 统计 UTF-16 code unit，Buffer.byteLength 统计编码字节', () => {
  const text = 'A中💡';
  const utf8 = Buffer.from(text, 'utf8');

  assert.equal(text.length, 4);
  assert.equal(Buffer.byteLength(text, 'utf8'), 8);
  assert.equal(utf8.length, 8);
  assert.equal(utf8.toString('utf8'), text);
  assert.equal(utf8.toString('hex'), '41e4b8adf09f92a1');
});

test('hex、base64 与 base64url 可往返同一字节序列', () => {
  const bytes = Buffer.from([0xfb, 0xff, 0x00, 0x10]);

  assert.equal(bytes.toString('hex'), 'fbff0010');
  assert.equal(bytes.toString('base64'), '+/8AEA==');
  assert.equal(bytes.toString('base64url'), '-_8AEA');
  assert.deepEqual(Buffer.from('-_8AEA', 'base64url'), bytes);
  assert.deepEqual(Buffer.from('+/8AEA==', 'base64'), bytes);

  // base64 解码器也接受 URL-safe 字母；输出 base64url 默认省略 padding。
  assert.deepEqual(Buffer.from('-_8AEA', 'base64'), bytes);
});

test('hex 解码遇到奇数位或非法字符会静默截断', () => {
  assert.deepEqual([...Buffer.from('1a7', 'hex')], [0x1a]);
  assert.deepEqual([...Buffer.from('1ag123', 'hex')], [0x1a]);

  // 处理不可信协议字段时先验证完整格式，不能只看 Buffer.from 是否抛错。
  const strictHex = (text) => {
    if (!/^(?:[0-9a-f]{2})+$/i.test(text)) {
      throw new TypeError('完整偶数位 hex 才有效');
    }
    return Buffer.from(text, 'hex');
  };
  assert.deepEqual([...strictHex('1a7f')], [0x1a, 0x7f]);
  assert.throws(() => strictHex('1a7'), TypeError);
});

test('从 ArrayBuffer 创建 Buffer 共享存储，从 TypedArray 创建则复制元素', () => {
  const arrayBuffer = new ArrayBuffer(4);
  const bytes = new Uint8Array(arrayBuffer);
  bytes.set([1, 2, 3, 4]);

  const shared = Buffer.from(arrayBuffer, 1, 2);
  const copied = Buffer.from(bytes);
  shared[0] = 9;

  assert.deepEqual([...bytes], [1, 9, 3, 4]);
  assert.deepEqual([...shared], [9, 3]);
  assert.deepEqual([...copied], [1, 2, 3, 4]);
  assert.equal(shared.buffer, arrayBuffer);
  assert.notEqual(copied.buffer, arrayBuffer);
});

test('Buffer 的 slice 和 subarray 都是共享视图，Buffer.from 才复制', () => {
  const original = Buffer.from([1, 2, 3, 4]);
  const sliced = original.slice(1, 3);
  const subarray = original.subarray(1, 3);
  const copied = Buffer.from(subarray);

  sliced[0] = 9;
  subarray[1] = 8;

  assert.deepEqual([...original], [1, 9, 8, 4]);
  assert.deepEqual([...sliced], [9, 8]);
  assert.deepEqual([...copied], [2, 3]);

  // 这与 Uint8Array.prototype.slice 的复制语义不同，是 Buffer 常见共享内存陷阱。
});

test('整数读写必须明确宽度、有无符号和字节序', () => {
  const buffer = Buffer.alloc(12);
  buffer.writeUInt16BE(0x1234, 0);
  buffer.writeUInt16LE(0x1234, 2);
  buffer.writeInt32BE(-2, 4);
  buffer.writeUInt32LE(0x89abcdef, 8);

  assert.equal(buffer.toString('hex'), '12343412fffffffeefcdab89');
  assert.equal(buffer.readUInt16BE(0), 0x1234);
  assert.equal(buffer.readUInt16LE(2), 0x1234);
  assert.equal(buffer.readInt32BE(4), -2);
  assert.equal(buffer.readUInt32LE(8), 0x89abcdef);
  assert.throws(() => buffer.readUInt32BE(10), RangeError);
});

test('浮点和 64 位整数读写保留各自的 Number/BigInt 模型', () => {
  const buffer = Buffer.alloc(24);
  buffer.writeFloatLE(1.5, 0);
  buffer.writeDoubleBE(Math.PI, 4);
  buffer.writeBigInt64LE(-2n, 12);

  assert.equal(buffer.readFloatLE(0), 1.5);
  assert.equal(buffer.readDoubleBE(4), Math.PI);
  assert.equal(buffer.readBigInt64LE(12), -2n);
  assert.equal(typeof buffer.readBigInt64LE(12), 'bigint');
  assert.throws(() => buffer.writeBigInt64LE(1, 12), TypeError);
});

test('compare/equals/search 使用字节语义，concat 可合并多个视图', () => {
  const first = Buffer.from('abc');
  const second = Buffer.from('abd');

  assert.ok(Buffer.compare(first, second) < 0);
  assert.equal(first.equals(Buffer.from('abc')), true);
  assert.equal(first.indexOf('b'), 1);
  assert.equal(first.includes(Buffer.from('bc')), true);

  const combined = Buffer.concat([first, Buffer.from('-'), second]);
  assert.equal(combined.toString(), 'abc-abd');
  assert.equal(Buffer.concat([first, second], 4).toString(), 'abca');
});

test('swap16/32/64 就地改变字节组，长度必须对齐', () => {
  const words = Buffer.from('00112233', 'hex');
  assert.equal(words.swap16(), words);
  assert.equal(words.toString('hex'), '11003322');

  const integers = Buffer.from('0011223344556677', 'hex');
  integers.swap32();
  assert.equal(integers.toString('hex'), '3322110077665544');
  assert.throws(() => Buffer.alloc(3).swap16(), RangeError);
});

test('toJSON 输出可恢复的 Buffer 标记记录，inspect 使用十六进制摘要', () => {
  const buffer = Buffer.from([1, 2, 255]);
  const json = JSON.stringify(buffer);

  assert.equal(json, '{"type":"Buffer","data":[1,2,255]}');
  assert.deepEqual(Buffer.from(JSON.parse(json)), buffer);
  assert.equal(buffer.toString(), '\u0001\u0002�');
  assert.match(buffer.inspect(), /^<Buffer 01 02 ff>$/);
});
