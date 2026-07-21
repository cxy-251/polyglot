// polyglot-covers:
// - nodejs.language.iterator-from
// - nodejs.language.iterator-helper-laziness
// - nodejs.language.iterator-map-filter-flat-map
// - nodejs.language.iterator-take-drop
// - nodejs.language.iterator-reduce-and-consumers
// - nodejs.language.iterator-helper-closing
// - nodejs.language.iterator-helper-single-use

import assert from 'node:assert/strict';
import test from 'node:test';

test('Iterator.from 把 iterable 或 iterator 规范化为 Iterator 实例', () => {
  const fromArray = Iterator.from([1, 2, 3]);
  assert.equal(fromArray instanceof Iterator, true);
  assert.equal(fromArray[Symbol.iterator](), fromArray);
  assert.deepEqual(fromArray.toArray(), [1, 2, 3]);

  const bareIterator = {
    current: 0,
    next() {
      this.current += 1;
      return this.current <= 2
        ? { done: false, value: this.current }
        : { done: true, value: undefined };
    },
  };
  assert.deepEqual(Iterator.from(bareIterator).toArray(), [1, 2]);
});

test('map/filter helper 是惰性的，消费时才拉取源值', () => {
  const events = [];
  function* source() {
    for (const value of [1, 2, 3]) {
      events.push(`source:${value}`);
      yield value;
    }
  }

  const helper = source()
    .map((value) => {
      events.push(`map:${value}`);
      return value * 2;
    })
    .filter((value) => {
      events.push(`filter:${value}`);
      return value > 2;
    });

  assert.deepEqual(events, []);
  assert.deepEqual(helper.next(), { done: false, value: 4 });
  assert.deepEqual(events, [
    'source:1',
    'map:1',
    'filter:2',
    'source:2',
    'map:2',
    'filter:4',
  ]);
});

test('take 限制元素数并关闭源，drop 跳过前缀', () => {
  const events = [];
  function* source() {
    try {
      yield 1;
      yield 2;
      yield 3;
      yield 4;
    } finally {
      events.push('source closed');
    }
  }

  assert.deepEqual(source().drop(2).take(2).toArray(), [3, 4]);
  assert.deepEqual(events, ['source closed']);

  assert.deepEqual([1, 2].values().take(0).toArray(), []);
  assert.throws(() => [1].values().take(-1), RangeError);
  assert.throws(() => [1].values().drop(-1), RangeError);
});

test('flatMap 要求回调结果可迭代并按顺序展平一层', () => {
  const result = [1, 2, 3]
    .values()
    .flatMap((value) => [value, value * 10])
    .toArray();

  assert.deepEqual(result, [1, 10, 2, 20, 3, 30]);
  assert.throws(
    () => [1].values().flatMap(() => 7).next(),
    TypeError,
  );
});

test('reduce 支持或省略初始值，空 iterator 无初始值会抛错', () => {
  assert.equal(
    [1, 2, 3].values().reduce((total, value) => total + value, 10),
    16,
  );
  assert.equal(
    [1, 2, 3].values().reduce((total, value) => total + value),
    6,
  );
  assert.throws(
    () => [].values().reduce((total, value) => total + value),
    TypeError,
  );
});

test('some、every 和 find 短路并关闭剩余源数据', () => {
  const closures = [];
  function* source(label) {
    try {
      yield 1;
      yield 2;
      yield 3;
    } finally {
      closures.push(label);
    }
  }

  assert.equal(source('some').some((value) => value === 2), true);
  assert.equal(source('every').every((value) => value < 2), false);
  assert.equal(source('find').find((value) => value > 1), 2);
  assert.deepEqual(closures, ['some', 'every', 'find']);
});

test('forEach 传递值与索引，toArray 收集剩余元素', () => {
  const seen = [];
  [10, 20, 30].values().forEach((value, index) => {
    seen.push([index, value]);
  });
  assert.deepEqual(seen, [[0, 10], [1, 20], [2, 30]]);

  const iterator = ['a', 'b', 'c'].values();
  assert.deepEqual(iterator.next(), { done: false, value: 'a' });
  assert.deepEqual(iterator.toArray(), ['b', 'c']);
});

test('helper 与源 iterator 共享单次游标，不是可重复查询集合', () => {
  const source = [1, 2, 3].values();
  const mapped = source.map((value) => value * 2);

  assert.deepEqual(mapped.next(), { done: false, value: 2 });
  assert.deepEqual(source.next(), { done: false, value: 2 });
  assert.deepEqual(mapped.toArray(), [6]);
  assert.deepEqual(source.next(), { done: true, value: undefined });
});

test('回调抛错时 helper 关闭源 iterator 并传播原异常', () => {
  const events = [];
  function* source() {
    try {
      yield 1;
      yield 2;
    } finally {
      events.push('closed');
    }
  }

  const failure = new Error('mapping failed');
  const mapped = source().map(() => {
    throw failure;
  });

  assert.throws(() => mapped.next(), (error) => error === failure);
  assert.deepEqual(events, ['closed']);
});
