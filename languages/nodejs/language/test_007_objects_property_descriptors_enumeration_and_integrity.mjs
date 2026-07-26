// polyglot-covers:
// - nodejs.language.object-property-keys
// - nodejs.language.data-and-accessor-descriptors
// - nodejs.language-property-definition-and-assignment
// - nodejs.language.object-literal-spread-and-proto-setter
// - nodejs.language.object-assign-versus-spread
// - nodejs.language.own-property-key-order
// - nodejs.language.object-integrity-levels
// - nodejs.language.in-and-object-has-own

// 跨语言迁移提示：JavaScript 属性由键、描述符和原型链定义，并可被 Proxy 拦截；
// Python 使用属性钩子与 descriptor 协议，C++ 成员布局和虚分派则在静态类型系统中建立。

import assert from 'node:assert/strict';
import test from 'node:test';

test('普通属性键转换为字符串，Symbol 键保持独立', () => {
  const symbol = Symbol('id');
  const record = {
    1: 'number syntax',
    [symbol]: 'symbol value',
  };

  record[{}] = 'object converted to string';

  assert.equal(record[1], 'number syntax');
  assert.equal(record['1'], 'number syntax');
  assert.equal(record['[object Object]'], 'object converted to string');
  assert.equal(record[symbol], 'symbol value');
  assert.deepEqual(Reflect.ownKeys(record), ['1', '[object Object]', symbol]);
});

test('数据描述符控制值与可写性，访问器描述符控制读取和写入', () => {
  const record = {};
  let stored = 1;

  Object.defineProperties(record, {
    fixed: {
      configurable: false,
      enumerable: true,
      value: 7,
      writable: false,
    },
    computed: {
      configurable: true,
      enumerable: false,
      get() {
        return stored * 2;
      },
      set(value) {
        stored = value;
      },
    },
  });

  assert.equal(record.fixed, 7);
  assert.throws(() => {
    record.fixed = 8;
  }, TypeError);

  record.computed = 5;
  assert.equal(record.computed, 10);
  assert.deepEqual(Object.keys(record), ['fixed']);
});

test('defineProperty 省略的布尔特性默认为 false', () => {
  const record = {};
  Object.defineProperty(record, 'hidden', { value: 1 });

  assert.deepEqual(Object.getOwnPropertyDescriptor(record, 'hidden'), {
    configurable: false,
    enumerable: false,
    value: 1,
    writable: false,
  });
  assert.deepEqual(Object.keys(record), []);
  assert.throws(() => {
    record.hidden = 2;
  }, TypeError);
  assert.throws(() => delete record.hidden, TypeError);
});

test('赋值会沿原型链查找 setter，定义自有属性不会调用它', () => {
  const events = [];
  const prototype = {
    set value(next) {
      events.push(next);
    },
  };
  const assigned = Object.create(prototype);
  const defined = Object.create(prototype);

  assigned.value = 3;
  Object.defineProperty(defined, 'value', {
    configurable: true,
    enumerable: true,
    value: 4,
    writable: true,
  });

  assert.deepEqual(events, [3]);
  assert.equal(Object.hasOwn(assigned, 'value'), false);
  assert.equal(Object.hasOwn(defined, 'value'), true);
  assert.equal(defined.value, 4);
});

test('对象字面量的 __proto__ setter 与普通计算属性不同', () => {
  const prototype = { inherited: 1 };
  const withPrototype = {
    __proto__: prototype,
    own: 2,
  };
  const withDataProperty = {
    ['__proto__']: prototype,
  };

  assert.equal(Object.getPrototypeOf(withPrototype), prototype);
  assert.equal(Object.hasOwn(withPrototype, '__proto__'), false);
  assert.equal(Object.getPrototypeOf(withDataProperty), Object.prototype);
  assert.equal(Object.hasOwn(withDataProperty, '__proto__'), true);
});

test('对象展开读取值并定义数据属性，Object.assign 使用普通 Set', () => {
  const events = [];
  const source = {
    get value() {
      events.push('get source');
      return 7;
    },
  };
  const target = {
    set value(next) {
      events.push(`set target:${next}`);
    },
  };

  Object.assign(target, source);
  const spread = { ...target, ...source };

  assert.deepEqual(events, ['get source', 'set target:7', 'get source']);
  assert.equal(spread.value, 7);
  assert.deepEqual(Object.getOwnPropertyDescriptor(spread, 'value'), {
    configurable: true,
    enumerable: true,
    value: 7,
    writable: true,
  });
});

test('对象展开只复制自有可枚举属性且是浅复制', () => {
  const nested = { count: 1 };
  const prototype = { inherited: 2 };
  const source = Object.assign(Object.create(prototype), {
    visible: 3,
    nested,
  });
  Object.defineProperty(source, 'hidden', {
    enumerable: false,
    value: 4,
  });

  const copy = { ...source };
  assert.deepEqual(Object.keys(copy), ['visible', 'nested']);
  assert.equal(copy.nested, nested);
  assert.equal('inherited' in copy, false);
  assert.equal('hidden' in copy, false);
});

test('自有键顺序先整数索引，再字符串插入顺序，最后 Symbol', () => {
  const firstSymbol = Symbol('first');
  const secondSymbol = Symbol('second');
  const record = {};

  record.beta = 1;
  record[10] = 2;
  record[2] = 3;
  record.alpha = 4;
  record[firstSymbol] = 5;
  record[secondSymbol] = 6;

  assert.deepEqual(Reflect.ownKeys(record), [
    '2',
    '10',
    'beta',
    'alpha',
    firstSymbol,
    secondSymbol,
  ]);
});

test('in 检查原型链，Object.hasOwn 只检查自有属性', () => {
  const prototype = { inherited: undefined };
  const record = Object.create(prototype);
  record.own = undefined;

  assert.equal('own' in record, true);
  assert.equal('inherited' in record, true);
  assert.equal('missing' in record, false);
  assert.equal(Object.hasOwn(record, 'own'), true);
  assert.equal(Object.hasOwn(record, 'inherited'), false);

  // 读取 undefined 无法区分“属性不存在”与“属性存在且值为 undefined”。
  assert.equal(record.own, record.missing);
});

test('preventExtensions、seal 和 freeze 逐步提高完整性，但都是浅层', () => {
  const nested = { count: 1 };
  const frozen = Object.freeze({ nested, fixed: 2 });

  assert.equal(Object.isExtensible(frozen), false);
  assert.equal(Object.isSealed(frozen), true);
  assert.equal(Object.isFrozen(frozen), true);
  assert.throws(() => {
    frozen.extra = 3;
  }, TypeError);
  assert.throws(() => {
    frozen.fixed = 4;
  }, TypeError);

  nested.count = 9;
  assert.equal(frozen.nested.count, 9);

  const sealed = Object.seal({ value: 1 });
  sealed.value = 2;
  assert.equal(sealed.value, 2);
  assert.throws(() => delete sealed.value, TypeError);
});
