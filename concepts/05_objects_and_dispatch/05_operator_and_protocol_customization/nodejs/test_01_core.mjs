// 运算符与协议定制。
// 共同问题：类型能否重载运算符；左右操作数如何协商；转换协议何时触发；
// 不支持的组合在编译期还是运行期失败。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: operator_and_protocol_customization
// polyglot-related: languages/nodejs/language/test_025_primitive_conversion_and_well_known_symbol_protocols.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class Distance {
  constructor(meters) {
    this.meters = meters;
  }

  [Symbol.toPrimitive](hint) {
    return hint === 'string' ? `${this.meters}m` : this.meters;
  }
}

test('Symbol.toPrimitive 定制运算前的原始值转换', () => {
  const distance = new Distance(3);

  assert.equal(distance + 2, 5);
  assert.equal(`${distance}`, '3m');
});

test('转换钩子不能让加法返回领域对象', () => {
  const result = new Distance(2) + new Distance(3);

  assert.equal(result, 5);
  assert.equal(result instanceof Distance, false);

  // JavaScript 没有 Python/C++ 的通用运算符重载；+ 仍执行内置原始值算法。
});

test('well-known Symbol 为特定语法提供协议入口', () => {
  const value = {
    *[Symbol.iterator]() {
      yield 1;
      yield 2;
    },
  };

  assert.deepEqual([...value], [1, 2]);
});

test('对象不能覆盖 ToBoolean', () => {
  const zero = new Distance(0);

  assert.equal(Boolean(zero), true);
  assert.equal(Number(zero), 0);
});

