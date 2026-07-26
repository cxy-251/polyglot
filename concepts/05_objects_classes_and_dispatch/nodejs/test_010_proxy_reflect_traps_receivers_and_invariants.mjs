// polyglot-covers:
// - nodejs.language.proxy-get-set-and-receiver
// - nodejs.language.proxy-has-delete-and-own-keys
// - nodejs.language.proxy-invariants
// - nodejs.language.proxy-revocation
// - nodejs.language.reflect-methods-and-forwarding
// - nodejs.language.reflect-construct-and-new-target
// - nodejs.language.proxy-private-field-brand-pitfall

import assert from 'node:assert/strict';
import test from 'node:test';

test('get 与 set trap 可以观察基本内部操作', () => {
  const events = [];
  const target = { count: 1 };
  const proxy = new Proxy(target, {
    get(object, key, receiver) {
      events.push(`get:${String(key)}`);
      return Reflect.get(object, key, receiver);
    },
    set(object, key, value, receiver) {
      events.push(`set:${String(key)}=${value}`);
      return Reflect.set(object, key, value, receiver);
    },
  });

  proxy.count += 2;
  assert.equal(proxy.count, 3);
  assert.equal(target.count, 3);
  assert.deepEqual(events, ['get:count', 'set:count=3', 'get:count']);

  // += 是一次读取再一次写入，因此会触发两个不同的内部操作，而不是单个“自增 trap”。
});

test('Reflect.get 的 receiver 决定访问器中的 this', () => {
  const base = {
    get total() {
      return this.left + this.right;
    },
  };
  const receiver = { left: 2, right: 3 };

  assert.equal(Reflect.get(base, 'total', receiver), 5);
  assert.equal(Reflect.get(base, 'total'), Number.NaN);

  const derived = Object.create(new Proxy(base, {
    get(target, key, actualReceiver) {
      return Reflect.get(target, key, actualReceiver);
    },
  }));
  derived.left = 4;
  derived.right = 6;
  assert.equal(derived.total, 10);
});

test('set trap 必须返回布尔成功信号，严格模式会检查它', () => {
  const target = {};
  const rejecting = new Proxy(target, {
    set() {
      return false;
    },
  });

  assert.throws(() => {
    rejecting.value = 1;
  }, TypeError);
  assert.equal(Object.hasOwn(target, 'value'), false);

  assert.equal(Reflect.set(rejecting, 'value', 1), false);
});

test('has、deleteProperty 和 ownKeys 对应不同表层操作', () => {
  const target = {
    visible: 1,
    secret: 2,
  };
  const proxy = new Proxy(target, {
    has(object, key) {
      return key === 'secret' ? false : Reflect.has(object, key);
    },
    deleteProperty(object, key) {
      return key === 'secret' ? false : Reflect.deleteProperty(object, key);
    },
    ownKeys(object) {
      return Reflect.ownKeys(object).filter((key) => key !== 'secret');
    },
  });

  assert.equal('secret' in proxy, false);
  assert.deepEqual(Object.keys(proxy), ['visible']);
  assert.equal(Reflect.deleteProperty(proxy, 'secret'), false);
  assert.equal(target.secret, 2);
});

test('Proxy 不能违反不可配置属性等目标不变量', () => {
  const target = {};
  Object.defineProperty(target, 'fixed', {
    configurable: false,
    enumerable: true,
    value: 1,
  });

  const hiding = new Proxy(target, {
    ownKeys() {
      return [];
    },
  });
  assert.throws(() => Reflect.ownKeys(hiding), TypeError);

  const lying = new Proxy(target, {
    getOwnPropertyDescriptor() {
      return undefined;
    },
  });
  assert.throws(() => Object.getOwnPropertyDescriptor(lying, 'fixed'), TypeError);
});

test('不可扩展目标要求 ownKeys 准确报告全部自有键', () => {
  const target = Object.preventExtensions({ first: 1 });
  const addingPhantom = new Proxy(target, {
    ownKeys() {
      return ['first', 'phantom'];
    },
  });

  assert.throws(() => Reflect.ownKeys(addingPhantom), TypeError);
});

test('Proxy.revocable 可明确切断对目标的代理访问', () => {
  const target = { value: 7 };
  const { proxy, revoke } = Proxy.revocable(target, {});

  assert.equal(proxy.value, 7);
  revoke();
  assert.throws(() => proxy.value, TypeError);
  assert.throws(() => Reflect.ownKeys(proxy), TypeError);

  // revoke 只让代理失效，不销毁目标；仍持有 target 的代码可以继续访问。
  assert.equal(target.value, 7);
});

test('Reflect.deleteProperty 以返回值表达失败，不触发严格模式语句异常', () => {
  const record = {};
  Object.defineProperty(record, 'fixed', {
    configurable: false,
    value: 1,
  });

  assert.equal(Reflect.deleteProperty(record, 'fixed'), false);
  assert.throws(() => delete record.fixed, TypeError);
  assert.equal(Reflect.defineProperty(record, 'extra', { value: 2 }), true);
  assert.equal(record.extra, 2);
});

test('Reflect.construct 可把实际构造函数与 new.target 原型分开', () => {
  class Base {
    constructor(value) {
      this.value = value;
      this.observedNewTarget = new.target.name;
    }
  }

  class Alternate {}

  const instance = Reflect.construct(Base, [7], Alternate);
  assert.equal(instance.value, 7);
  assert.equal(instance.observedNewTarget, 'Alternate');
  assert.equal(instance instanceof Base, false);
  assert.equal(instance instanceof Alternate, true);
});

test('透明转发代理仍可能破坏私有字段品牌检查', () => {
  class Secret {
    #value = 7;

    read() {
      return this.#value;
    }
  }

  const target = new Secret();
  const proxy = new Proxy(target, {});

  assert.equal(target.read(), 7);
  assert.throws(() => proxy.read(), TypeError);

  const bindingProxy = new Proxy(target, {
    get(object, key, receiver) {
      const value = Reflect.get(object, key, receiver);
      return typeof value === 'function' ? value.bind(object) : value;
    },
  });
  assert.equal(bindingProxy.read(), 7);

  // “自动绑定所有函数”也会改变函数身份和可覆盖性，只能作为特定封装的有意策略。
});
