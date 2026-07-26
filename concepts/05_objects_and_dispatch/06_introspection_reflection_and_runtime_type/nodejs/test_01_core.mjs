// 自省、反射与运行时类型。
// 共同问题：如何查询真实类型与成员；能否动态读写和调用；反射是否触发用户代码；
// 哪些检查只存在于编译期。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: introspection_reflection_and_runtime_type
// polyglot-related: languages/nodejs/language/test_010_proxy_reflect_traps_receivers_and_invariants.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

class Service {
  run(value = 1) {
    return value * 2;
  }
}

test('typeof、instanceof 与原型查询回答不同类型问题', () => {
  const service = new Service();

  assert.equal(typeof service, 'object');
  assert.equal(service instanceof Service, true);
  assert.equal(Object.getPrototypeOf(service), Service.prototype);
});

test('Reflect 动态读取、写入和调用', () => {
  const service = new Service();
  const operation = Reflect.get(service, 'run');

  assert.equal(Reflect.apply(operation, service, [3]), 6);
  assert.equal(Reflect.set(service, 'name', 'alpha'), true);
  assert.equal(service.name, 'alpha');
});

test('ownKeys 和描述符只查看自有结构', () => {
  const service = new Service();
  service.name = 'alpha';

  assert.deepEqual(Reflect.ownKeys(service), ['name']);
  assert.equal(Object.getOwnPropertyDescriptor(service, 'name').value, 'alpha');
  assert.equal(Object.hasOwn(service, 'run'), false);
});

test('Proxy 让反射操作本身触发用户代码', () => {
  const events = [];
  const service = new Proxy(new Service(), {
    get(target, key, receiver) {
      events.push(String(key));
      return Reflect.get(target, key, receiver);
    },
  });

  assert.equal(service.run(2), 4);
  assert.deepEqual(events, ['run']);
});
