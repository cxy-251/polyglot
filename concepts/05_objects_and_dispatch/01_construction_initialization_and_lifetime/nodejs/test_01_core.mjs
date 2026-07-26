// 对象构造、初始化与生命周期。
// 共同问题：分配与初始化能否分开；复制是否自动发生；销毁时机是否确定；
// 类型如何定制创建结果。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: construction_initialization_and_lifetime
// polyglot-related: languages/nodejs/language/test_008_prototypes_classes_fields_and_private_elements.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('new 创建对象、设置原型并以该对象调用 constructor', () => {
  class Record {
    constructor(value) {
      this.value = value;
    }
  }

  const record = new Record(3);

  assert.equal(record.value, 3);
  assert.equal(Object.getPrototypeOf(record), Record.prototype);
});

test('构造器显式返回对象会替换默认实例', () => {
  class Factory {
    constructor() {
      return { created: true };
    }
  }

  const value = new Factory();

  assert.deepEqual(value, { created: true });
  assert.equal(value instanceof Factory, false);
});

test('对象赋值只复制引用，结构复制必须显式进行', () => {
  const original = { nested: [1] };
  const alias = original;
  const shallow = { ...original };

  assert.equal(alias, original);
  assert.notEqual(shallow, original);
  assert.equal(shallow.nested, original.nested);
});

test('普通对象没有确定的作用域析构时点', () => {
  const value = { state: 'alive' };

  assert.equal(value.state, 'alive');

  // FinalizationRegistry 回调时点不可预测；同步资源应使用 using/Symbol.dispose，不依赖 GC。
});

