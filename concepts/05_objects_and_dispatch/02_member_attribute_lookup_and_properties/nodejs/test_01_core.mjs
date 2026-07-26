// 成员、属性查找与 property。
// 共同问题：实例与类型成员的查找顺序是什么；访问器如何获得接收者；
// 数据描述符能否覆盖实例字典；缺失属性如何定制。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: member_attribute_lookup_and_properties
// polyglot-related: languages/nodejs/language/test_007_objects_property_descriptors_enumeration_and_integrity.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('属性读取先查自有属性，再沿原型链查找', () => {
  const prototype = { label: 'prototype' };
  const value = Object.create(prototype);

  assert.equal(value.label, 'prototype');
  value.label = 'own';
  assert.equal(value.label, 'own');
  delete value.label;
  assert.equal(value.label, 'prototype');
});

test('getter 中的 this 是实际接收者', () => {
  const prototype = {
    get doubled() {
      return this.value * 2;
    },
  };
  const value = Object.assign(Object.create(prototype), { value: 5 });

  assert.equal(value.doubled, 10);
  assert.equal(Reflect.get(prototype, 'doubled', { value: 7 }), 14);
});

test('数据属性可以遮蔽原型访问器，除非访问器定义 setter', () => {
  const prototype = {};
  Object.defineProperty(prototype, 'label', {
    get() {
      return 'prototype';
    },
    configurable: true,
  });
  const value = Object.create(prototype);
  Object.defineProperty(value, 'label', { value: 'own' });

  assert.equal(value.label, 'own');
});

test('Proxy get trap 可以定制缺失属性', () => {
  const value = new Proxy({ present: 1 }, {
    get(target, key, receiver) {
      return Reflect.has(target, key) ? Reflect.get(target, key, receiver) : `missing:${String(key)}`;
    },
  });

  assert.equal(value.present, 1);
  assert.equal(value.unknown, 'missing:unknown');
});
