// 封装、私有状态与只读边界。
// 共同问题：私有成员由语法还是约定保护；只读是否深层生效；
// 调用方能否绕过封装；类型如何暴露受控更新。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: encapsulation_private_state_and_immutability
// polyglot-related: languages/nodejs/language/test_008_prototypes_classes_fields_and_private_elements.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class Account {
  #balance;

  constructor(balance) {
    this.#balance = balance;
  }

  get balance() {
    return this.#balance;
  }

  deposit(amount) {
    this.#balance += amount;
  }
}

test('私有字段按类品牌检查，不是字符串属性', () => {
  const account = new Account(10);

  assert.equal(account.balance, 10);
  assert.equal(account['#balance'], undefined);
  assert.deepEqual(Object.keys(account), []);
});

test('提取私有字段访问器后不能换接收者', () => {
  const descriptor = Object.getOwnPropertyDescriptor(Account.prototype, 'balance');

  assert.throws(() => descriptor.get.call({}), TypeError);
});

test('Object.freeze 阻止表层属性修改但不是深冻结', () => {
  const value = Object.freeze({ nested: { count: 1 } });

  assert.throws(() => {
    value.extra = true;
  }, TypeError);

  value.nested.count = 2;
  assert.equal(value.nested.count, 2);
});

test('getter 提供只读表面，方法仍可受控更新私有状态', () => {
  const account = new Account(10);

  assert.throws(() => {
    account.balance = 20;
  }, TypeError);

  account.deposit(5);
  assert.equal(account.balance, 15);
});
