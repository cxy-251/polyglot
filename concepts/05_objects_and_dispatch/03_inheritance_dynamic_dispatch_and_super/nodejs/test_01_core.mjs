// 继承、动态分派与 super。
// 共同问题：覆盖方法如何动态选择；基类实现如何调用；多继承顺序如何确定；
// 把派生对象当基类使用是否丢失动态类型。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: inheritance_dynamic_dispatch_and_super
// polyglot-related: languages/nodejs/language/test_009_class_inheritance_super_static_blocks_and_mixins.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class Base {
  describe() {
    return ['base'];
  }
}

class Derived extends Base {
  describe() {
    return ['derived', ...super.describe()];
  }
}

test('原型方法查找使用实际对象，因此覆盖方法动态生效', () => {
  const value = new Derived();

  assert.deepEqual(value.describe(), ['derived', 'base']);
  assert.equal(value instanceof Base, true);
});

test('super 从基类原型取方法但保留当前 this', () => {
  class NamedBase {
    describe() {
      return this.name;
    }
  }
  class NamedDerived extends NamedBase {
    constructor(name) {
      super();
      this.name = name;
    }
  }

  assert.equal(new NamedDerived('value').describe(), 'value');
});

test('显式调用基类方法可以绕过覆盖查找', () => {
  const value = new Derived();

  assert.deepEqual(Base.prototype.describe.call(value), ['base']);
});

test('class 只支持单一 extends，组合通常使用 mixin 或委托', () => {
  const timestamped = (Parent) => class extends Parent {
    timestamp() {
      return 1;
    }
  };
  class Mixed extends timestamped(Base) {}

  const value = new Mixed();
  assert.deepEqual(value.describe(), ['base']);
  assert.equal(value.timestamp(), 1);
});
