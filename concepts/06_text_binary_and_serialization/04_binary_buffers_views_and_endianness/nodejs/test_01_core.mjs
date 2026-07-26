// 二进制缓冲区、视图与字节序。
// 共同问题：字节存储是否可变；视图是否共享内存；多字节整数如何选择端序；
// 复制与别名边界在哪里。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/nodejs/language/test_012_arraybuffer_typedarray_dataview_and_binary_memory.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('ArrayBuffer 是存储，TypedArray 是带元素类型的视图', () => {
  const storage = new ArrayBuffer(4);
  const first = new Uint8Array(storage);
  const second = new Uint8Array(storage);

  first[0] = 9;

  assert.equal(second[0], 9);
  assert.equal(first.buffer, storage);
});

test('subarray 共享存储，slice 复制元素', () => {
  const source = new Uint8Array([1, 2, 3]);
  const shared = source.subarray(1);
  const copied = source.slice(1);
  source[1] = 9;

  assert.deepEqual([...shared], [9, 3]);
  assert.deepEqual([...copied], [2, 3]);
});

test('DataView 为每次多字节读写显式选择端序', () => {
  const storage = new ArrayBuffer(4);
  const view = new DataView(storage);

  view.setUint32(0, 0x01020304, false);

  assert.deepEqual([...new Uint8Array(storage)], [1, 2, 3, 4]);
  assert.equal(view.getUint32(0, false), 0x01020304);
  assert.equal(view.getUint32(0, true), 0x04030201);
});

test('TypedArray 元素赋值按位宽转换', () => {
  const values = new Uint8Array([256, -1, 257]);

  assert.deepEqual([...values], [0, 255, 1]);
});

