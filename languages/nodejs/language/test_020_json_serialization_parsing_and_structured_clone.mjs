// polyglot-covers:
// - nodejs.language.json-stringify-supported-values
// - nodejs.language.json-to-json-replacer-and-space
// - nodejs.language.json-parse-reviver-and-source
// - nodejs.language.json-cycles-numbers-and-prototype-keys
// - nodejs.language.structured-clone-types-and-cycles
// - nodejs.language.structured-clone-prototypes-and-properties
// - nodejs.language.structured-clone-transfer

import assert from 'node:assert/strict';
import test from 'node:test';

test('JSON 对对象属性与数组元素中的不支持值采用不同策略', () => {
  const value = {
    absent: undefined,
    callable() {},
    symbol: Symbol('value'),
    array: [undefined, () => undefined, Symbol('value')],
    valid: null,
  };

  assert.equal(JSON.stringify(value), '{"array":[null,null,null],"valid":null}');
  assert.equal(JSON.stringify(undefined), undefined);
  assert.equal(JSON.stringify(Number.NaN), 'null');
  assert.equal(JSON.stringify(Infinity), 'null');
  assert.throws(() => JSON.stringify(1n), TypeError);
});

test('toJSON 在 replacer 之前改变待序列化值', () => {
  const events = [];
  const value = {
    secret: 'hidden',
    toJSON(key) {
      events.push(`toJSON:${key}`);
      return { visible: 7, omitted: 8 };
    },
  };

  const json = JSON.stringify({ value }, (key, current) => {
    events.push(`replacer:${key}`);
    return key === 'omitted' ? undefined : current;
  });

  assert.equal(json, '{"value":{"visible":7}}');
  assert.deepEqual(events, [
    'replacer:',
    'toJSON:value',
    'replacer:value',
    'replacer:visible',
    'replacer:omitted',
  ]);
});

test('replacer 数组筛选对象键，space 只影响格式', () => {
  const value = {
    id: 1,
    name: 'Ada',
    secret: 'hidden',
  };

  assert.equal(
    JSON.stringify(value, ['name', 'id'], 2),
    '{\n  "name": "Ada",\n  "id": 1\n}',
  );
});

test('parse reviver 从叶到根运行，返回 undefined 会删除属性', () => {
  const visited = [];
  const value = JSON.parse(
    '{"created":"2026-07-22","remove":1,"nested":{"count":2}}',
    (key, current) => {
      visited.push(key);
      if (key === 'created') {
        return new Date(`${current}T00:00:00.000Z`);
      }
      if (key === 'remove') {
        return undefined;
      }
      return current;
    },
  );

  assert.equal(value.created instanceof Date, true);
  assert.equal(Object.hasOwn(value, 'remove'), false);
  assert.deepEqual(value.nested, { count: 2 });
  assert.deepEqual(visited, ['created', 'remove', 'count', 'nested', '']);
});

test('带 source context 的 reviver 可无损恢复超大整数', {
  skip: (() => {
    let available = false;
    JSON.parse('1', (key, value, context) => {
      available = key === '' && context?.source === '1';
      return value;
    });
    return !available;
  })(),
}, () => {
  const parsed = JSON.parse(
    '{"id":9007199254740993}',
    (key, value, context) => key === 'id' ? BigInt(context.source) : value,
  );

  assert.equal(parsed.id, 9007199254740993n);
  // value 参数在 reviver 前已经作为 Number 丢失精度，必须使用原始 token 的 source。
});

test('JSON 拒绝循环引用，且特殊数值不会往返保持', () => {
  const cyclic = {};
  cyclic.self = cyclic;
  assert.throws(() => JSON.stringify(cyclic), TypeError);

  const roundTrip = JSON.parse(JSON.stringify({
    infinity: Infinity,
    nan: Number.NaN,
    negativeZero: -0,
  }));
  assert.deepEqual(roundTrip, {
    infinity: null,
    nan: null,
    negativeZero: 0,
  });
  assert.equal(Object.is(roundTrip.negativeZero, -0), false);
});

test('解析 __proto__ 产生普通自有属性，不会调用对象字面量 setter', () => {
  const value = JSON.parse('{"__proto__":{"polluted":true}}');

  assert.equal(Object.hasOwn(value, '__proto__'), true);
  assert.equal(value.__proto__.polluted, true);
  assert.equal(Object.getPrototypeOf(value), Object.prototype);
  assert.equal({}.polluted, undefined);

  // 后续把不可信结果合并到其他对象时仍需防范原型污染；安全解析不代表任意合并也安全。
});

test('structuredClone 支持循环、共享引用和多种内置对象', () => {
  const shared = { value: 1 };
  const original = {
    date: new Date('2026-07-22T00:00:00.000Z'),
    map: new Map([['key', shared]]),
    regexp: /polyglot/gi,
    set: new Set([shared]),
    shared,
  };
  original.self = original;

  const cloned = structuredClone(original);
  assert.notEqual(cloned, original);
  assert.equal(cloned.self, cloned);
  assert.equal(cloned.date instanceof Date, true);
  assert.equal(cloned.date.toISOString(), original.date.toISOString());
  assert.equal(cloned.regexp instanceof RegExp, true);
  assert.equal(cloned.regexp.source, 'polyglot');
  assert.equal(cloned.regexp.flags, 'gi');
  assert.equal(cloned.map.get('key'), cloned.shared);
  assert.equal([...cloned.set][0], cloned.shared);
});

test('structuredClone 复制二进制存储而不默认共享', () => {
  const original = Uint8Array.from([1, 2, 3]);
  const cloned = structuredClone(original);

  assert.equal(cloned instanceof Uint8Array, true);
  assert.deepEqual([...cloned], [1, 2, 3]);
  assert.notEqual(cloned.buffer, original.buffer);

  cloned[0] = 9;
  assert.equal(original[0], 1);
});

test('structuredClone 不保留用户类原型、私有字段或属性描述符', () => {
  class Record {
    #secret = 9;

    constructor() {
      Object.defineProperty(this, 'fixed', {
        enumerable: true,
        value: 7,
        writable: false,
      });
    }

    readSecret() {
      return this.#secret;
    }
  }

  const cloned = structuredClone(new Record());
  assert.equal(cloned instanceof Record, false);
  assert.equal(Object.getPrototypeOf(cloned), Object.prototype);
  assert.equal(cloned.fixed, 7);
  assert.equal(Object.getOwnPropertyDescriptor(cloned, 'fixed').writable, true);
  assert.equal(cloned.readSecret, undefined);
});

test('structuredClone 不能复制函数、Symbol 和 WeakMap', () => {
  assert.throws(() => structuredClone(() => undefined), {
    name: 'DataCloneError',
  });
  assert.throws(() => structuredClone(Symbol('value')), {
    name: 'DataCloneError',
  });
  assert.throws(() => structuredClone(new WeakMap()), {
    name: 'DataCloneError',
  });
});

test('transfer 可零复制转移 ArrayBuffer 并分离原缓冲区', () => {
  const buffer = new ArrayBuffer(4);
  new Uint8Array(buffer).set([1, 2, 3, 4]);

  const cloned = structuredClone({ buffer }, { transfer: [buffer] });
  assert.equal(buffer.byteLength, 0);
  assert.equal(buffer.detached, true);
  assert.deepEqual([...new Uint8Array(cloned.buffer)], [1, 2, 3, 4]);

  // transfer 是所有权移动；原有视图之后不可继续使用，调用方必须把这一点纳入 API 契约。
});
