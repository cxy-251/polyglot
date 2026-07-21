// polyglot-covers:
// - nodejs.language.operator-precedence-and-associativity
// - nodejs.language.expression-evaluation-order
// - nodejs.language.short-circuit-operators
// - nodejs.language.logical-assignment
// - nodejs.language.optional-chaining
// - nodejs.language.unary-and-delete-operators
// - nodejs.language.bitwise-operators
// - nodejs.language.assignment-and-comma-expressions

import assert from 'node:assert/strict';
import test from 'node:test';

test('优先级决定分组，求幂和赋值按右结合', () => {
  assert.equal(2 + 3 * 4, 14);
  assert.equal((2 + 3) * 4, 20);
  assert.equal(2 ** 3 ** 2, 512);
  assert.equal((2 ** 3) ** 2, 64);

  let left;
  let right;
  left = right = 9;
  assert.deepEqual([left, right], [9, 9]);

  // 一元负号不能直接位于求幂表达式左侧；必须通过括号说明是先取负还是先求幂。
  assert.throws(() => new Function('return -2 ** 2;'), SyntaxError);
  assert.equal(-(2 ** 2), -4);
  assert.equal((-2) ** 2, 4);
});

test('操作数一般从左到右求值，即使运算符按右结合分组', () => {
  const events = [];
  const value = (label, result) => {
    events.push(label);
    return result;
  };

  const result = value('base', 2) ** value('middle', 3) ** value('right', 2);
  assert.equal(result, 512);
  assert.deepEqual(events, ['base', 'middle', 'right']);
});

test('逻辑运算符返回实际操作数并短路右侧求值', () => {
  const events = [];
  const record = (label, value) => {
    events.push(label);
    return value;
  };

  assert.equal(record('zero', 0) && record('not reached', 1), 0);
  assert.equal(record('empty', '') || record('fallback', 'value'), 'value');
  assert.equal(record('null', null) ?? record('nullish', 'value'), 'value');
  assert.equal(record('false', false) ?? record('kept false', true), false);

  assert.deepEqual(events, ['zero', 'empty', 'fallback', 'null', 'nullish', 'false']);
});

test('逻辑赋值只在需要时取值和写回属性', () => {
  const events = [];
  const state = { value: 0 };
  const proxy = new Proxy(state, {
    get(target, key, receiver) {
      events.push(`get:${String(key)}`);
      return Reflect.get(target, key, receiver);
    },
    set(target, key, value, receiver) {
      events.push(`set:${String(key)}=${value}`);
      return Reflect.set(target, key, value, receiver);
    },
  });

  proxy.value ??= 10;
  assert.deepEqual(events, ['get:value']);

  proxy.value ||= 20;
  assert.equal(proxy.value, 20);
  assert.deepEqual(events, ['get:value', 'get:value', 'set:value=20', 'get:value']);

  // x ||= y 不是简单的 x = x || y：属性引用只求值一次，而且短路时完全不写回。
});

test('可选链同时短路属性键、调用参数和连续链', () => {
  let evaluations = 0;
  const next = () => {
    evaluations += 1;
    return 'value';
  };

  const absent = null;
  assert.equal(absent?.[next()], undefined);
  assert.equal(absent?.method(next()), undefined);
  assert.equal(evaluations, 0);

  const present = {
    nested: {
      value: 7,
    },
  };
  assert.equal(present?.nested?.value, 7);
  assert.equal(present?.missing?.value, undefined);

  // 括号结束了连续的可选链；后续普通属性访问仍会对 undefined 抛错。
  assert.throws(() => (absent?.nested).value, TypeError);
});

test('可选调用保留成员引用的 this，但提取函数会丢失接收者', () => {
  const counter = {
    count: 4,
    read() {
      return this.count;
    },
  };

  assert.equal(counter.read?.(), 4);
  const detached = counter.read;
  assert.throws(() => detached?.(), TypeError);
});

test('typeof 未声明标识符是特例，TDZ 内绑定仍会抛错', () => {
  assert.equal(typeof completelyUndeclaredName, 'undefined');

  const inspectTemporalDeadZone = () => {
    const result = typeof localName;
    let localName = 'ready';
    return result;
  };
  assert.throws(inspectTemporalDeadZone, ReferenceError);
  assert.equal(void 123, undefined);
});

test('delete 删除属性而不是局部绑定，返回值也不表示属性曾存在', () => {
  const record = {
    configurable: 1,
  };
  Object.defineProperty(record, 'fixed', {
    configurable: false,
    value: 2,
  });

  assert.equal(delete record.configurable, true);
  assert.equal(delete record.missing, true);
  assert.throws(() => delete record.fixed, TypeError);
  assert.deepEqual(Reflect.ownKeys(record), ['fixed']);
});

test('位运算先把 Number 转成 32 位整数', () => {
  assert.equal(0xffff_ffff | 0, -1);
  assert.equal(2 ** 32 | 0, 0);
  assert.equal(-1 >>> 0, 0xffff_ffff);
  assert.equal(5 << 1, 10);
  assert.equal(5 & 1, 1);

  // 位运算不是通用的快速取整：超出 32 位会截断。Math.trunc 保留安全整数范围内的值。
  assert.equal(3_000_000_000 | 0, -1_294_967_296);
  assert.equal(Math.trunc(3_000_000_000.9), 3_000_000_000);
});

test('逗号表达式返回最后一个值，并会把成员引用变成普通值', () => {
  const owner = {
    value: 8,
    read() {
      return this.value;
    },
  };

  assert.equal((1, 2, 3), 3);
  assert.equal(owner.read(), 8);

  // (0, owner.read) 的最终结果只是函数值，不再携带 owner 这个引用基值。
  assert.throws(() => (0, owner.read)(), TypeError);
});
