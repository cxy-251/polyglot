// 对象身份、别名与复制。
// 共同问题：赋值是否复制对象；浅复制保留哪些别名；深复制如何处理对象图；
// 语言如何表达独占或共享所有权。
//
// polyglot-family: values_and_comparison
// polyglot-concept: identity_aliasing_and_copying
// polyglot-related: languages/nodejs/language/test_007_objects_property_descriptors_enumeration_and_integrity.mjs
// polyglot-related: languages/nodejs/language/test_020_json_serialization_parsing_and_structured_clone.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('对象赋值复制引用值，因此两个绑定指向同一对象', () => {
  const original = { items: [1] };
  const alias = original;

  alias.items.push(2);

  assert.equal(alias, original);
  assert.deepEqual(original, { items: [1, 2] });
});

test('对象展开只浅复制自有可枚举属性', () => {
  const original = { items: [1] };
  const copied = { ...original };

  copied.items.push(2);

  assert.notEqual(copied, original);
  assert.equal(copied.items, original.items);
  assert.deepEqual(original.items, [1, 2]);
});

test('structuredClone 复制嵌套对象并保留循环图拓扑', () => {
  const original = { items: [1] };
  original.self = original;

  const cloned = structuredClone(original);
  cloned.items.push(2);

  assert.notEqual(cloned, original);
  assert.notEqual(cloned.items, original.items);
  assert.deepEqual(original.items, [1]);
  assert.equal(cloned.self, cloned);
});

test('语言对象没有 C++ 式独占所有权类型', () => {
  const value = { count: 1 };
  const owners = [value, value];

  assert.equal(owners[0], owners[1]);

  // 引用由垃圾回收器追踪；普通赋值无法声明 unique_ptr 式“只能移动、不能复制”的所有权。
});

