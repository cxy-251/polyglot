// 序列化、克隆与所有权转移。
// 共同问题：哪些值可以跨边界编码；对象图复制是否保留别名和循环；
// 自定义类型如何参与；反序列化是否安全。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/nodejs/language/test_020_json_serialization_parsing_and_structured_clone.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('JSON round trip 只覆盖 JSON 数据模型', () => {
  const original = { items: [1, true, null], missing: undefined };
  const decoded = JSON.parse(JSON.stringify(original));

  assert.deepEqual(decoded, { items: [1, true, null] });
  assert.equal(Object.hasOwn(decoded, 'missing'), false);
});

test('toJSON 和 reviver 提供显式扩展点', () => {
  const value = {
    x: 3,
    toJSON() {
      return { type: 'Point', x: this.x };
    },
  };
  const decoded = JSON.parse(JSON.stringify(value), (key, item) =>
    item?.type === 'Point' ? { x: item.x, restored: true } : item);

  assert.deepEqual(decoded, { x: 3, restored: true });
});

test('structuredClone 保留循环和共享引用', () => {
  const child = {};
  const original = { first: child, second: child };
  original.self = original;

  const cloned = structuredClone(original);

  assert.equal(cloned.first, cloned.second);
  assert.equal(cloned.self, cloned);
  assert.notEqual(cloned.first, child);
});

test('transfer 移交 ArrayBuffer 并分离原存储', () => {
  const original = new ArrayBuffer(4);
  new Uint8Array(original)[0] = 9;

  const cloned = structuredClone(original, { transfer: [original] });

  assert.equal(original.byteLength, 0);
  assert.equal(new Uint8Array(cloned)[0], 9);
});
