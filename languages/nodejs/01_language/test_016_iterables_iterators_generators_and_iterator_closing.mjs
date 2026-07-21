// polyglot-covers:
// - nodejs.language.iterable-and-iterator-protocols
// - nodejs.language.built-in-iterators
// - nodejs.language.iterator-closing
// - nodejs.language.generator-state-and-next-values
// - nodejs.language.generator-return-throw-and-finally
// - nodejs.language.yield-star-delegation
// - nodejs.language.generator-as-iterable-iterator

import assert from 'node:assert/strict';
import test from 'node:test';

test('iterable 负责创建 iterator，iterator 的 next 产生结果记录', () => {
  const range = {
    start: 2,
    end: 4,
    [Symbol.iterator]() {
      let current = this.start;
      const end = this.end;
      return {
        next() {
          if (current <= end) {
            const value = current;
            current += 1;
            return { done: false, value };
          }
          return { done: true, value: undefined };
        },
      };
    },
  };

  assert.deepEqual([...range], [2, 3, 4]);
  assert.deepEqual([...range], [2, 3, 4]);

  const iterator = range[Symbol.iterator]();
  assert.deepEqual(iterator.next(), { done: false, value: 2 });
  assert.deepEqual(iterator.next(), { done: false, value: 3 });
});

test('iterator 也可以让自身成为单次 iterable iterator', () => {
  const iterator = {
    current: 0,
    next() {
      this.current += 1;
      return this.current <= 3
        ? { done: false, value: this.current }
        : { done: true, value: undefined };
    },
    [Symbol.iterator]() {
      return this;
    },
  };

  assert.equal(iterator[Symbol.iterator](), iterator);
  assert.deepEqual([...iterator], [1, 2, 3]);
  assert.deepEqual([...iterator], []);

  // 生成器和许多内置迭代器是一次性的；容器对象通常每次迭代创建新 iterator。
});

test('展开、数组解构、for-of 与集合构造器都会消费 iterable', () => {
  const values = new Set(['a', 'b', 'c']);

  const [first, ...remaining] = values;
  assert.equal(first, 'a');
  assert.deepEqual(remaining, ['b', 'c']);
  assert.deepEqual([...values], ['a', 'b', 'c']);
  assert.deepEqual([...new Map(values.entries())], [
    ['a', 'a'],
    ['b', 'b'],
    ['c', 'c'],
  ]);
});

test('提前退出 for-of 会调用 iterator.return 完成清理', () => {
  const events = [];
  const iterable = {
    [Symbol.iterator]() {
      let current = 0;
      return {
        next() {
          events.push(`next:${current}`);
          return { done: false, value: current++ };
        },
        return() {
          events.push('return');
          return { done: true, value: undefined };
        },
      };
    },
  };

  for (const value of iterable) {
    assert.equal(value, 0);
    break;
  }
  assert.deepEqual(events, ['next:0', 'return']);
});

test('正常耗尽不调用 return，解构只取部分元素时会调用', () => {
  const events = [];
  const makeIterable = () => ({
    [Symbol.iterator]() {
      let current = 0;
      return {
        next() {
          current += 1;
          return current <= 2
            ? { done: false, value: current }
            : { done: true, value: undefined };
        },
        return() {
          events.push('closed');
          return { done: true };
        },
      };
    },
  });

  assert.deepEqual([...makeIterable()], [1, 2]);
  assert.deepEqual(events, []);

  const [first] = makeIterable();
  assert.equal(first, 1);
  assert.deepEqual(events, ['closed']);
});

test('生成器调用先返回暂停对象，首次 next 才执行函数体', () => {
  const events = [];

  function* sequence() {
    events.push('start');
    yield 'first';
    events.push('resume');
    return 'finished';
  }

  const generator = sequence();
  assert.deepEqual(events, []);
  assert.equal(generator[Symbol.iterator](), generator);

  assert.deepEqual(generator.next(), { done: false, value: 'first' });
  assert.deepEqual(events, ['start']);
  assert.deepEqual(generator.next(), { done: true, value: 'finished' });
  assert.deepEqual(events, ['start', 'resume']);
  assert.deepEqual(generator.next(), { done: true, value: undefined });
});

test('传给 next 的值成为上一个 yield 表达式的结果', () => {
  function* conversation() {
    const name = yield 'name?';
    const age = yield `hello ${name}, age?`;
    return { age, name };
  }

  const generator = conversation();
  assert.deepEqual(generator.next('ignored'), { done: false, value: 'name?' });
  assert.deepEqual(generator.next('Ada'), {
    done: false,
    value: 'hello Ada, age?',
  });
  assert.deepEqual(generator.next(36), {
    done: true,
    value: { age: 36, name: 'Ada' },
  });

  // 首次 next 的参数没有暂停中的 yield 可以接收，因此会被忽略。
});

test('return 和 throw 从外部改变生成器控制流，finally 仍执行', () => {
  const events = [];

  function* resource() {
    try {
      events.push('open');
      yield 1;
      yield 2;
    } catch (error) {
      events.push(`caught:${error.message}`);
      yield 'recovered';
    } finally {
      events.push('close');
    }
  }

  const returned = resource();
  assert.deepEqual(returned.next(), { done: false, value: 1 });
  assert.deepEqual(returned.return('stop'), { done: true, value: 'stop' });
  assert.deepEqual(events, ['open', 'close']);

  events.length = 0;
  const thrown = resource();
  thrown.next();
  assert.deepEqual(thrown.throw(new Error('failure')), {
    done: false,
    value: 'recovered',
  });
  assert.deepEqual(thrown.next(), { done: true, value: undefined });
  assert.deepEqual(events, ['open', 'caught:failure', 'close']);
});

test('yield* 委托另一个 iterable，并取得其最终 return 值', () => {
  function* inner() {
    yield 1;
    yield 2;
    return 'inner result';
  }

  function* outer() {
    yield 0;
    const result = yield* inner();
    yield result;
  }

  assert.deepEqual([...outer()], [0, 1, 2, 'inner result']);
  assert.deepEqual([...function* () {
    yield* 'AB';
  }()], ['A', 'B']);
});
