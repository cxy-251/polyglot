// polyglot-covers:
// - nodejs.language.array-index-properties-and-length
// - nodejs.language.array-holes-versus-undefined
// - nodejs.language.array-mutating-methods
// - nodejs.language.array-copying-methods
// - nodejs.language.array-iteration-methods
// - nodejs.language.array-sort-and-stability
// - nodejs.language.array-construction-and-conversion
// - nodejs.language.array-concat-spreadability-and-species

import assert from 'node:assert/strict';
import test from 'node:test';

test('数组索引是特殊字符串属性，length 自动跟踪最高索引', () => {
  const values = [];
  values[2] = 'third';

  assert.equal(values.length, 3);
  assert.equal(0 in values, false);
  assert.equal(2 in values, true);
  assert.deepEqual(Object.keys(values), ['2']);

  values['01'] = 'ordinary property';
  values[-1] = 'also ordinary';
  assert.equal(values.length, 3);
  assert.deepEqual(Object.keys(values), ['2', '01', '-1']);
});

test('空槽与值为 undefined 的元素在部分操作中不同', () => {
  const sparse = [, undefined, 2];
  const visited = [];
  sparse.forEach((value, index) => visited.push([index, value]));

  assert.equal(sparse.length, 3);
  assert.equal(0 in sparse, false);
  assert.equal(1 in sparse, true);
  assert.deepEqual(visited, [[1, undefined], [2, 2]]);

  // 迭代器把空槽读成 undefined，而 forEach/map/filter 等许多回调方法跳过空槽。
  assert.deepEqual([...sparse], [undefined, undefined, 2]);
  assert.deepEqual(Array.from(sparse), [undefined, undefined, 2]);
  assert.equal(sparse.includes(undefined), true);
});

test('增大 length 创建空槽，缩小 length 会删除尾部属性', () => {
  const values = ['a', 'b', 'c'];
  values.length = 5;

  assert.equal(values.length, 5);
  assert.equal(3 in values, false);

  values.length = 1;
  assert.deepEqual(values, ['a']);
  assert.equal(1 in values, false);

  assert.throws(() => {
    values.length = -1;
  }, RangeError);
});

test('push/pop 与 shift/unshift 从不同端修改同一个数组', () => {
  const queue = ['middle'];
  assert.equal(queue.push('last'), 2);
  assert.equal(queue.unshift('first'), 3);
  assert.deepEqual(queue, ['first', 'middle', 'last']);

  assert.equal(queue.pop(), 'last');
  assert.equal(queue.shift(), 'first');
  assert.deepEqual(queue, ['middle']);

  // shift/unshift 通常需要重排后续索引；大队列更适合维护头指针或专门的数据结构。
});

test('splice 同时表达删除、插入和替换，并返回被删除元素', () => {
  const values = ['a', 'b', 'c', 'd'];
  const removed = values.splice(1, 2, 'x', 'y', 'z');

  assert.deepEqual(removed, ['b', 'c']);
  assert.deepEqual(values, ['a', 'x', 'y', 'z', 'd']);

  values.splice(-1, 0, 'before last');
  assert.deepEqual(values, ['a', 'x', 'y', 'z', 'before last', 'd']);
});

test('现代 copying 方法返回新数组而不修改原数组', () => {
  const original = [3, 1, 2];

  assert.deepEqual(original.toSorted((left, right) => left - right), [1, 2, 3]);
  assert.deepEqual(original.toReversed(), [2, 1, 3]);
  assert.deepEqual(original.toSpliced(1, 1, 9, 8), [3, 9, 8, 2]);
  assert.deepEqual(original.with(-1, 7), [3, 1, 7]);
  assert.deepEqual(original, [3, 1, 2]);

  assert.throws(() => original.with(3, 0), RangeError);
});

test('slice 是浅复制，fill 和 copyWithin 会就地修改', () => {
  const nested = { value: 1 };
  const original = [nested, 2, 3, 4];
  const copy = original.slice(0, 2);

  assert.notEqual(copy, original);
  assert.equal(copy[0], nested);

  const filled = [0, 0, 0, 0];
  assert.equal(filled.fill(7, 1, 3), filled);
  assert.deepEqual(filled, [0, 7, 7, 0]);

  const moved = [1, 2, 3, 4, 5];
  moved.copyWithin(1, 3);
  assert.deepEqual(moved, [1, 4, 5, 4, 5]);
});

test('map、filter、reduce 与 flatMap 表达不同的数据流', () => {
  const values = [1, 2, 3, 4];

  assert.deepEqual(values.map((value) => value * 2), [2, 4, 6, 8]);
  assert.deepEqual(values.filter((value) => value % 2 === 0), [2, 4]);
  assert.equal(values.reduce((total, value) => total + value, 0), 10);
  assert.deepEqual(
    values.flatMap((value) => (value % 2 === 0 ? [value, -value] : [])),
    [2, -2, 4, -4],
  );

  assert.throws(() => [].reduce((left, right) => left + right), TypeError);
});

test('some/every/find/findLast 可以短路，findIndex 返回位置', () => {
  const values = [1, 3, 6, 8];
  let checks = 0;

  assert.equal(values.some((value) => {
    checks += 1;
    return value % 2 === 0;
  }), true);
  assert.equal(checks, 3);

  assert.equal(values.every((value) => value > 0), true);
  assert.equal(values.find((value) => value % 2 === 0), 6);
  assert.equal(values.findLast((value) => value % 2 === 0), 8);
  assert.equal(values.findIndex((value) => value === 6), 2);
  assert.equal(values.findIndex((value) => value === 99), -1);
});

test('默认 sort 按字符串排序，数值排序必须提供比较器', () => {
  const values = [2, 10, 1, 20];

  assert.deepEqual(values.toSorted(), [1, 10, 2, 20]);
  assert.deepEqual(values.toSorted((left, right) => left - right), [1, 2, 10, 20]);

  const records = [
    { group: 2, id: 'a' },
    { group: 1, id: 'b' },
    { group: 2, id: 'c' },
    { group: 1, id: 'd' },
  ];
  const sorted = records.toSorted((left, right) => left.group - right.group);
  assert.deepEqual(sorted.map(({ id }) => id), ['b', 'd', 'a', 'c']);
  // 规范要求稳定排序，因此比较器返回 0 的元素保持原相对顺序。
});

test('Array 构造器的单个数值参数表示长度而不是元素', () => {
  const byLength = Array(3);
  const byElements = Array.of(3);

  assert.equal(byLength.length, 3);
  assert.equal(0 in byLength, false);
  assert.deepEqual(byElements, [3]);
  assert.deepEqual(Array.from({ length: 3 }, (_, index) => index), [0, 1, 2]);
  assert.deepEqual(Array.from('A💡'), ['A', '💡']);
});

test('concat 默认展开数组，也接受 Symbol.isConcatSpreadable 协议', () => {
  const arrayLike = {
    0: 'x',
    1: 'y',
    length: 2,
    [Symbol.isConcatSpreadable]: true,
  };
  const keptArray = ['a', 'b'];
  keptArray[Symbol.isConcatSpreadable] = false;

  assert.deepEqual([0].concat(arrayLike, 3), [0, 'x', 'y', 3]);
  assert.deepEqual([0].concat(keptArray), [0, keptArray]);
});

test('Array 子类可用 Symbol.species 控制旧式派生方法的结果构造器', () => {
  class PlainResultArray extends Array {
    static get [Symbol.species]() {
      return Array;
    }
  }

  const values = new PlainResultArray(1, 2, 3);
  const mapped = values.map((value) => value * 2);

  assert.equal(mapped instanceof PlainResultArray, false);
  assert.equal(mapped instanceof Array, true);
  assert.deepEqual(mapped, [2, 4, 6]);

  // 新的 toSorted 等 copying 方法总是创建普通 Array，不使用 Symbol.species。
  assert.equal(values.toSorted() instanceof PlainResultArray, false);
});
