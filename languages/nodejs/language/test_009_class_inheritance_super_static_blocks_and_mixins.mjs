// polyglot-covers:
// - nodejs.language.class-extends-and-super-construction
// - nodejs.language.super-property-access
// - nodejs.language-derived-field-initialization-order
// - nodejs.language.static-members-and-inheritance
// - nodejs.language.static-initialization-blocks
// - nodejs.language.class-expressions-and-mixins
// - nodejs.language-subclass-constructor-return

import assert from 'node:assert/strict';
import test from 'node:test';

test('派生构造器必须在读取 this 前调用 super', () => {
  class Base {
    constructor(name) {
      this.name = name;
    }
  }

  class Valid extends Base {
    constructor(name, role) {
      super(name);
      this.role = role;
    }
  }

  class Invalid extends Base {
    constructor() {
      this.value = 1;
      super('late');
    }
  }

  const valid = new Valid('Ada', 'admin');
  assert.deepEqual({ name: valid.name, role: valid.role }, {
    name: 'Ada',
    role: 'admin',
  });
  assert.equal(valid instanceof Valid, true);
  assert.throws(() => new Invalid(), ReferenceError);
});

test('super.method 从基类原型取方法，但调用时 this 仍是当前实例', () => {
  class Formatter {
    constructor(prefix) {
      this.prefix = prefix;
    }

    format(value) {
      return `${this.prefix}${value}`;
    }
  }

  class BracketFormatter extends Formatter {
    format(value) {
      return `[${super.format(value)}]`;
    }
  }

  const formatter = new BracketFormatter('#');
  assert.equal(formatter.format('item'), '[#item]');
});

test('基类字段先初始化，派生字段在 super 返回后初始化', () => {
  const events = [];

  class Base {
    baseField = events.push('base field');

    constructor() {
      events.push('base constructor');
    }
  }

  class Derived extends Base {
    derivedField = events.push('derived field');

    constructor() {
      events.push('before super');
      super();
      events.push('after super');
    }
  }

  const instance = new Derived();
  assert.equal(instance.baseField, 2);
  assert.equal(instance.derivedField, 4);
  assert.deepEqual(events, [
    'before super',
    'base field',
    'base constructor',
    'derived field',
    'after super',
  ]);
});

test('字段初始化使用最终接收者，但基类构造期间派生字段尚不存在', () => {
  class Base {
    constructor() {
      this.observedInBase = this.derivedValue;
    }
  }

  class Derived extends Base {
    derivedValue = 7;
  }

  const instance = new Derived();
  assert.equal(instance.observedInBase, undefined);
  assert.equal(instance.derivedValue, 7);
});

test('静态成员通过构造器原型链继承，并以派生类作为 this', () => {
  class Registry {
    static category = 'base';

    static describe() {
      return this.category;
    }
  }

  class SpecializedRegistry extends Registry {
    static category = 'specialized';
  }

  assert.equal(Registry.describe(), 'base');
  assert.equal(SpecializedRegistry.describe(), 'specialized');
  assert.equal(Object.getPrototypeOf(SpecializedRegistry), Registry);
  assert.equal(Object.getPrototypeOf(SpecializedRegistry.prototype), Registry.prototype);
});

test('静态初始化块按文本顺序执行并可访问私有静态状态', () => {
  const events = [];

  class Configuration {
    static #prefix = 'polyglot';

    static first = events.push('field:first');

    static {
      events.push(`block:${this.#prefix}`);
      this.label = `${this.#prefix}-nodejs`;
    }

    static last = events.push('field:last');
  }

  assert.deepEqual(events, ['field:first', 'block:polyglot', 'field:last']);
  assert.equal(Configuration.label, 'polyglot-nodejs');
});

test('class 表达式可作为 mixin 工厂的返回值', () => {
  const Timestamped = (Base) => class extends Base {
    setTimestamp(value) {
      this.timestamp = value;
      return this;
    }
  };

  const Tagged = (Base) => class extends Base {
    setTag(value) {
      this.tag = value;
      return this;
    }
  };

  class Record {
    constructor(id) {
      this.id = id;
    }
  }

  class EnrichedRecord extends Tagged(Timestamped(Record)) {}

  const record = new EnrichedRecord(1).setTimestamp(100).setTag('ready');
  assert.deepEqual(
    { id: record.id, timestamp: record.timestamp, tag: record.tag },
    { id: 1, timestamp: 100, tag: 'ready' },
  );
  assert.equal(record instanceof Record, true);
});

test('派生构造器可以返回对象而不调用 super，但不能返回原始值', () => {
  class Base {}

  class ObjectReplacement extends Base {
    constructor() {
      return { replacement: true };
    }
  }

  class PrimitiveReplacement extends Base {
    constructor() {
      return 1;
    }
  }

  assert.deepEqual(new ObjectReplacement(), { replacement: true });
  assert.throws(() => new PrimitiveReplacement(), TypeError);
});

test('extends null 创建无普通对象原型的类，但默认构造器无法自动 super', () => {
  class NullPrototype extends null {
    constructor(value) {
      const instance = Object.create(new.target.prototype);
      instance.value = value;
      return instance;
    }
  }

  const instance = new NullPrototype(7);
  assert.equal(instance.value, 7);
  assert.equal(instance instanceof NullPrototype, true);
  assert.equal(Object.getPrototypeOf(NullPrototype.prototype), null);
  assert.equal(instance.toString, undefined);
});
