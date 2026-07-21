// polyglot-covers:
// - nodejs.language.this-binding-modes
// - nodejs.language.method-reference-and-receiver
// - nodejs.language.arrow-lexical-this-and-arguments
// - nodejs.language.function-call-apply-and-bind
// - nodejs.language.bound-function-construction
// - nodejs.language.getter-setter-receiver
// - nodejs.language.top-level-this-in-esm

import assert from 'node:assert/strict';
import test from 'node:test';

test('ESM 顶层 this 是 undefined，普通函数的 this 由调用方式决定', () => {
  assert.equal(this, undefined);

  function readName() {
    return this.name;
  }
  const owner = { name: 'owner', readName };

  assert.equal(owner.readName(), 'owner');
  assert.equal(readName.call({ name: 'call receiver' }), 'call receiver');
  assert.throws(() => readName(), TypeError);

  // 模块和类体是严格模式。普通函数直接调用不会把 this 替换为 globalThis，也不会把
  // null/undefined 自动装箱，这比脚本中的旧式 sloppy 行为更可预测。
});

test('成员访问产生携带接收者的引用，提取函数只保留函数值', () => {
  const counter = {
    count: 3,
    increment(step = 1) {
      this.count += step;
      return this.count;
    },
  };

  assert.equal(counter.increment(2), 5);

  const detached = counter.increment;
  assert.throws(() => detached(1), TypeError);

  const other = { count: 10 };
  assert.equal(detached.call(other, 4), 14);
  assert.equal(other.count, 14);
  assert.equal(counter.count, 5);
});

test('箭头函数捕获外围 this，不会被 call、apply 或 bind 改写', () => {
  const owner = {
    name: 'lexical owner',
    createReader() {
      return () => this.name;
    },
  };

  const reader = owner.createReader();
  assert.equal(reader(), 'lexical owner');
  assert.equal(reader.call({ name: 'ignored' }), 'lexical owner');
  assert.equal(reader.apply({ name: 'ignored' }), 'lexical owner');
  assert.equal(reader.bind({ name: 'ignored' })(), 'lexical owner');
});

test('箭头函数也从外围捕获 arguments', () => {
  function createInspector(first) {
    const inspect = () => ({
      first,
      argumentCount: arguments.length,
      secondArgument: arguments[1],
    });
    return inspect;
  }

  assert.deepEqual(createInspector('a', 'b')(), {
    first: 'a',
    argumentCount: 2,
    secondArgument: 'b',
  });

  // 需要独立参数集合时使用 rest；箭头函数没有自己的 arguments，也不能作为构造函数。
  const collect = (...values) => values;
  assert.deepEqual(collect(1, 2, 3), [1, 2, 3]);
  assert.throws(() => new collect(), TypeError);
});

test('bind 固定 this 和前置参数，并通过 length/name 暴露部分信息', () => {
  function format(prefix, value, suffix) {
    return `${prefix}${this.label}:${value}${suffix}`;
  }

  const bound = format.bind({ label: 'item' }, '[', 7);
  assert.equal(bound(']'), '[item:7]');
  assert.equal(bound.length, 1);
  assert.equal(bound.name, 'bound format');

  // 再次 bind 不能替换第一次固定的 this，但可以继续追加前置参数。
  const rebound = bound.bind({ label: 'ignored' }, '>');
  assert.equal(rebound(), '[item:7>');
});

test('bound 构造函数忽略绑定的 this，但保留前置构造参数', () => {
  function Point(x, y) {
    this.x = x;
    this.y = y;
  }

  const ignoredReceiver = { x: -1, y: -1 };
  const PointAtTen = Point.bind(ignoredReceiver, 10);
  const point = new PointAtTen(20);

  assert.deepEqual({ x: point.x, y: point.y }, { x: 10, y: 20 });
  assert.equal(point instanceof Point, true);
  assert.equal(point instanceof PointAtTen, true);
  assert.deepEqual(ignoredReceiver, { x: -1, y: -1 });
});

test('getter 与 setter 中的 this 是实际属性接收者', () => {
  const prototype = {
    get summary() {
      return `${this.name}:${this._score}`;
    },
    set score(value) {
      this._score = Number(value);
    },
  };

  const first = Object.create(prototype);
  first.name = 'first';
  first.score = '7';

  const second = Object.create(prototype);
  second.name = 'second';
  second.score = '9';

  assert.equal(first.summary, 'first:7');
  assert.equal(second.summary, 'second:9');
  assert.equal(Object.hasOwn(first, '_score'), true);
  assert.equal(Object.hasOwn(prototype, '_score'), false);
});

test('回调的调用者通常不会保留原对象接收者', () => {
  class Collector {
    constructor(prefix) {
      this.prefix = prefix;
    }

    format(value) {
      return `${this.prefix}${value}`;
    }
  }

  const collector = new Collector('#');
  assert.throws(() => [1].map(collector.format), TypeError);

  assert.deepEqual([1, 2].map(collector.format, collector), ['#1', '#2']);
  assert.deepEqual([1, 2].map((value) => collector.format(value)), ['#1', '#2']);
  assert.deepEqual([1, 2].map(collector.format.bind(collector)), ['#1', '#2']);
});

test('类字段箭头函数按实例创建，原型方法则由实例共享', () => {
  class Handler {
    name;

    constructor(name) {
      this.name = name;
    }

    prototypeMethod() {
      return this.name;
    }

    fieldArrow = () => this.name;
  }

  const first = new Handler('first');
  const second = new Handler('second');

  assert.equal(first.prototypeMethod, second.prototypeMethod);
  assert.notEqual(first.fieldArrow, second.fieldArrow);
  assert.equal(first.fieldArrow.call(second), 'first');

  // 字段箭头便于作为回调，但每个实例都会分配函数，也无法由子类通过 super 覆盖调用。
});
