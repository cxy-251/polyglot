// polyglot-covers:
// - nodejs.language.map-keys-order-and-overwrite
// - nodejs.language.set-values-and-same-value-zero
// - nodejs.language.map-set-construction-and-iteration
// - nodejs.language.set-composition-methods
// - nodejs.language.weakmap-and-weakset
// - nodejs.language.weakref-and-finalization-registry-contract

import assert from 'node:assert/strict';
import test from 'node:test';

test('Map 接受任意键并保持首次插入顺序', () => {
  const objectKey = { id: 1 };
  const map = new Map([
    ['first', 1],
    [objectKey, 2],
    ['last', 3],
  ]);

  map.set('first', 10);
  assert.equal(map.size, 3);
  assert.equal(map.get(objectKey), 2);
  assert.equal(map.get({ id: 1 }), undefined);
  assert.deepEqual([...map.keys()], ['first', objectKey, 'last']);

  map.delete(objectKey);
  map.set(objectKey, 20);
  assert.deepEqual([...map.keys()], ['first', 'last', objectKey]);
});

test('Map 的 get(undefined) 不能区分缺失键，需要配合 has', () => {
  const map = new Map([
    ['present', undefined],
  ]);

  assert.equal(map.get('present'), undefined);
  assert.equal(map.get('missing'), undefined);
  assert.equal(map.has('present'), true);
  assert.equal(map.has('missing'), false);
});

test('Map 构造器消费二元 iterable，迭代默认产生 entry', () => {
  const entries = new Set([
    ['a', 1],
    ['b', 2],
  ]);
  const map = new Map(entries);

  assert.deepEqual([...map], [['a', 1], ['b', 2]]);
  assert.deepEqual([...map.entries()], [...map]);
  assert.deepEqual([...map.values()], [1, 2]);

  const seen = [];
  map.forEach((value, key, owner) => seen.push([key, value, owner === map]));
  assert.deepEqual(seen, [['a', 1, true], ['b', 2, true]]);
});

test('Set 去重使用 SameValueZero 并保持插入顺序', () => {
  const firstObject = { id: 1 };
  const secondObject = { id: 1 };
  const values = new Set([Number.NaN, Number.NaN, 0, -0, firstObject, secondObject]);

  assert.equal(values.size, 4);
  assert.equal(values.has(Number.NaN), true);
  assert.equal(values.has(-0), true);
  assert.deepEqual([...values], [Number.NaN, 0, firstObject, secondObject]);

  values.add(firstObject);
  assert.equal(values.size, 4);
});

test('Set 组合方法返回新集合且不修改操作数', {
  skip: typeof Set.prototype.union !== 'function',
}, () => {
  const left = new Set([1, 2, 3]);
  const right = new Set([3, 4]);

  assert.deepEqual([...left.union(right)], [1, 2, 3, 4]);
  assert.deepEqual([...left.intersection(right)], [3]);
  assert.deepEqual([...left.difference(right)], [1, 2]);
  assert.deepEqual([...left.symmetricDifference(right)], [1, 2, 4]);

  assert.equal(left.isSubsetOf(new Set([1, 2, 3, 4])), true);
  assert.equal(left.isSupersetOf(new Set([1, 2])), true);
  assert.equal(left.isDisjointFrom(new Set([4, 5])), true);
  assert.deepEqual([...left], [1, 2, 3]);
});

test('WeakMap 让附加状态不阻止对象键被回收', () => {
  const privateState = new WeakMap();

  class Counter {
    constructor(initial = 0) {
      privateState.set(this, { count: initial });
    }

    increment() {
      privateState.get(this).count += 1;
      return privateState.get(this).count;
    }
  }

  const counter = new Counter(5);
  assert.equal(counter.increment(), 6);
  assert.equal(privateState.has(counter), true);
  assert.throws(() => privateState.set('primitive', 1), TypeError);

  // WeakMap 不可枚举，也没有 size；否则枚举结果会暴露垃圾回收时机。
  assert.equal(privateState.size, undefined);
  assert.equal(privateState[Symbol.iterator], undefined);
});

test('WeakSet 适合记录对象身份而不拥有对象生命周期', () => {
  const processed = new WeakSet();
  const first = {};
  const second = {};

  processed.add(first);
  assert.equal(processed.has(first), true);
  assert.equal(processed.has(second), false);
  assert.equal(processed.delete(first), true);
  assert.equal(processed.has(first), false);
  assert.throws(() => processed.add(1), TypeError);
});

test('非注册 Symbol 可作为弱集合键，注册 Symbol 不可用', () => {
  const local = Symbol('local');
  const registered = Symbol.for('polyglot.registered');
  const map = new WeakMap();
  const set = new WeakSet();

  map.set(local, 'value');
  set.add(local);
  assert.equal(map.get(local), 'value');
  assert.equal(set.has(local), true);

  assert.throws(() => map.set(registered, 'value'), TypeError);
  assert.throws(() => set.add(registered), TypeError);
});

test('WeakRef 的 deref 只能用于机会性访问，不能证明回收时点', () => {
  const target = { value: 7 };
  const reference = new WeakRef(target);

  assert.equal(reference.deref(), target);
  assert.equal(typeof reference.deref, 'function');

  const registry = new FinalizationRegistry(() => {
    throw new Error('测试不应依赖终结回调执行');
  });
  const unregisterToken = {};
  registry.register(target, 'held value', unregisterToken);
  assert.equal(registry.unregister(unregisterToken), true);

  // 规范不保证何时甚至是否执行回收和终结回调；测试只验证同步 API，不调用 gc 或等待回收。
});
