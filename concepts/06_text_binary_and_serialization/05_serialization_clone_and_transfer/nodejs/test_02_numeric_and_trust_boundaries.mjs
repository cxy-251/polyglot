// 数值模型、类型恢复与信任边界。
// 共同问题：通用数据格式是否保留语言数值类型；非标准数值如何处理；
// 自定义反序列化如何限制可构造类型和字段。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/nodejs/language/test_020_json_serialization_parsing_and_structured_clone.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('JSON number 超过安全整数范围会按 Number 模型丢失精度', () => {
  const text = '9007199254740993';
  const decoded = JSON.parse(text);

  assert.equal(decoded, 9007199254740992);
  assert.notEqual(BigInt(decoded), BigInt(text));
  assert.throws(() => JSON.stringify(9007199254740993n), TypeError);

  // 若协议需要该整数，应编码为带规则的字符串并显式恢复 BigInt，不能静默 round trip。
});

test('reviver 只恢复白名单标签和字段', () => {
  function restore(key, value) {
    if (value?.type !== 'Point') {
      return value;
    }
    if (Object.keys(value).sort().join(',') !== 'type,x' || !Number.isInteger(value.x)) {
      throw new TypeError('invalid Point payload');
    }
    return { x: value.x, restored: true };
  }

  assert.deepEqual(
    JSON.parse('{"type":"Point","x":3}', restore),
    { x: 3, restored: true },
  );
  assert.throws(
    () => JSON.parse('{"type":"Point","x":"3","extra":true}', restore),
    /invalid Point payload/,
  );

  // reviver 不应根据输入字符串动态查找构造器或执行代码。
});

test('transfer 分离原 ArrayBuffer 及其既有视图', () => {
  const original = new ArrayBuffer(4);
  const originalView = new Uint8Array(original);
  originalView[0] = 9;

  const cloned = structuredClone(original, { transfer: [original] });

  assert.equal(original.byteLength, 0);
  assert.equal(originalView.byteLength, 0);
  assert.deepEqual([...new Uint8Array(cloned)], [9, 0, 0, 0]);

  // transfer 不是复制后继续共享；原 buffer 被 detach，既有 TypedArray 变为零长度。
});
