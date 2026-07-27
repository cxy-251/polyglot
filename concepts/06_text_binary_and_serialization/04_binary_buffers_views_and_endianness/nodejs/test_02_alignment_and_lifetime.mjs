// 未对齐访问、视图生命周期与复制边界。
// 共同问题：多字节访问是否要求对齐；共享视图何时阻止或失去底层存储；
// 协议读取如何避免依赖宿主对象布局。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/nodejs/language/test_012_arraybuffer_typedarray_dataview_and_binary_memory.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('DataView 支持未对齐偏移，TypedArray 构造要求元素对齐', () => {
  const storage = new ArrayBuffer(5);
  const view = new DataView(storage);

  view.setUint32(1, 0x01020304, false);

  assert.equal(view.getUint32(1, false), 0x01020304);
  assert.deepEqual([...new Uint8Array(storage)], [0, 1, 2, 3, 4]);
  assert.throws(() => new Uint32Array(storage, 1, 1), RangeError);
});

test('TypedArray slice 建立拥有型副本，subarray 继续共享', () => {
  const source = new Uint8Array([1, 2, 3]);
  const copied = source.slice();
  const shared = source.subarray();

  source[0] = 9;

  assert.deepEqual([...copied], [1, 2, 3]);
  assert.equal(shared[0], 9);

  // DataView/TypedArray 记录 buffer、offset、length；是否共享由构造方式决定，不能只从
  // 变量类型判断所有权。
});
