// polyglot-covers:
// - nodejs.language.prototype-chain-and-shadowing
// - nodejs.language.object-create-and-prototype-mutation
// - nodejs.language.class-definition-and-construction
// - nodejs.language.instance-methods-and-public-fields
// - nodejs.language.private-fields-methods-and-brand-checks
// - nodejs.language.class-strict-mode
// - nodejs.language-class-constructor-return-override

import assert from 'node:assert/strict';
import test from 'node:test';

test('属性读取沿原型链查找，自有属性可以遮蔽后再恢复', () => {
  const grandparent = { category: 'grandparent' };
  const parent = Object.create(grandparent);
  parent.value = 1;
  const child = Object.create(parent);

  assert.equal(child.value, 1);
  assert.equal(child.category, 'grandparent');
  assert.equal(Object.hasOwn(child, 'value'), false);

  child.value = 2;
  assert.equal(child.value, 2);
  assert.equal(parent.value, 1);
  assert.equal(Object.hasOwn(child, 'value'), true);

  delete child.value;
  assert.equal(child.value, 1);
});

test('Object.create 可同时指定原型和首批属性描述符', () => {
  const protocol = {
    describe() {
      return `${this.kind}:${this.id}`;
    },
  };
  const record = Object.create(protocol, {
    id: {
      enumerable: true,
      value: 7,
      writable: false,
    },
    kind: {
      enumerable: true,
      value: 'record',
      writable: true,
    },
  });

  assert.equal(record.describe(), 'record:7');
  assert.equal(Object.getPrototypeOf(record), protocol);
  assert.deepEqual(Object.keys(record), ['id', 'kind']);
  assert.throws(() => {
    record.id = 8;
  }, TypeError);
});

test('运行后替换构造函数 prototype 不会迁移既有实例', () => {
  function Item() {}
  const first = new Item();
  const originalPrototype = Item.prototype;

  Item.prototype = { category: 'replacement' };
  const second = new Item();

  assert.equal(Object.getPrototypeOf(first), originalPrototype);
  assert.equal(Object.getPrototypeOf(second), Item.prototype);
  assert.equal(first instanceof Item, false);
  assert.equal(second instanceof Item, true);

  // 修改原型对象本身会被既有实例看到；把 .prototype 指向新对象只影响以后构造的实例。
});

test('class 方法位于原型且不可枚举，公共字段是实例自有属性', () => {
  class Counter {
    count = 0;

    increment() {
      this.count += 1;
      return this.count;
    }
  }

  const first = new Counter();
  const second = new Counter();

  assert.equal(Object.hasOwn(first, 'count'), true);
  assert.equal(Object.hasOwn(first, 'increment'), false);
  assert.equal(first.increment, second.increment);
  assert.deepEqual(Object.keys(first), ['count']);
  assert.equal(
    Object.getOwnPropertyDescriptor(Counter.prototype, 'increment').enumerable,
    false,
  );
});

test('类声明处于 TDZ，且类构造器必须通过 new 调用', () => {
  const readBeforeDeclaration = () => {
    const value = Example;
    class Example {}
    return value;
  };
  assert.throws(readBeforeDeclaration, ReferenceError);

  class Record {}
  assert.throws(() => Record(), TypeError);
  assert.equal(new Record() instanceof Record, true);
});

test('私有字段按类的品牌而不是属性名访问', () => {
  class Vault {
    #value;

    constructor(value) {
      this.#value = value;
    }

    read() {
      return this.#value;
    }

    static owns(candidate) {
      return #value in candidate;
    }
  }

  const vault = new Vault(7);
  assert.equal(vault.read(), 7);
  assert.equal(Vault.owns(vault), true);
  assert.equal(Vault.owns({ '#value': 7 }), false);
  assert.equal(Object.hasOwn(vault, '#value'), false);
  assert.deepEqual(Reflect.ownKeys(vault), []);

  assert.throws(() => Vault.prototype.read.call({}), TypeError);
});

test('相同拼写的私有字段在不同类中仍是不同品牌', () => {
  class First {
    #value = 'first';

    static read(instance) {
      return instance.#value;
    }
  }

  class Second {
    #value = 'second';

    static read(instance) {
      return instance.#value;
    }
  }

  const first = new First();
  const second = new Second();
  assert.equal(First.read(first), 'first');
  assert.equal(Second.read(second), 'second');
  assert.throws(() => First.read(second), TypeError);
});

test('私有方法可共享实现，私有静态字段只属于类构造器', () => {
  class Normalizer {
    static #created = 0;

    constructor() {
      Normalizer.#created += 1;
    }

    #trim(value) {
      return String(value).trim();
    }

    normalize(value) {
      return this.#trim(value).toLowerCase();
    }

    static created() {
      return Normalizer.#created;
    }
  }

  const normalizer = new Normalizer();
  new Normalizer();
  assert.equal(normalizer.normalize('  VALUE  '), 'value');
  assert.equal(Normalizer.created(), 2);
});

test('基类构造器显式返回对象会替换实例并跳过原型关系', () => {
  class Replacing {
    field = 'unobserved';

    constructor() {
      return { replacement: true };
    }
  }

  const value = new Replacing();
  assert.deepEqual(value, { replacement: true });
  assert.equal(value instanceof Replacing, false);

  // 普通构造器返回原始值会被忽略；返回对象则替换新实例。除工厂适配等少数场景外，
  // 类构造器不应这样做，否则字段初始化结果和 instanceof 都会令人意外。
});

test('类体总是严格模式，提取的方法不会得到全局 this', () => {
  class Inspector {
    inspect() {
      return this;
    }
  }

  const instance = new Inspector();
  assert.equal(instance.inspect(), instance);

  const detached = instance.inspect;
  assert.equal(detached(), undefined);
});
