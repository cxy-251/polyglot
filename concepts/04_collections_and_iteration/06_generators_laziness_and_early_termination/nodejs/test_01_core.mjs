// 生成器、惰性与提前终止。
// 共同问题：何时执行生产逻辑；如何限制消费；提前终止是否运行清理；
// 惰性管道能否重复使用。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/nodejs/language/test_016_iterables_iterators_generators_and_iterator_closing.mjs
// polyglot-related: languages/nodejs/language/test_026_iterator_helpers_laziness_composition_and_closing.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('生成器函数体在第一次 next 前不执行', () => {
  const events = [];
  function* values() {
    events.push('start');
    yield 1;
    events.push('resume');
    yield 2;
  }

  const iterator = values();
  assert.deepEqual(events, []);
  assert.deepEqual(iterator.next(), { value: 1, done: false });
  assert.deepEqual(events, ['start']);
});

test('iterator helper 的 map 和 take 按消费惰性执行', () => {
  let calls = 0;
  const values = Iterator.from([1, 2, 3])
    .map((value) => {
      calls += 1;
      return value * 2;
    })
    .take(2);

  assert.equal(calls, 0);
  assert.deepEqual(values.toArray(), [2, 4]);
  assert.equal(calls, 2);
});

test('return 提前关闭生成器并执行 finally', () => {
  const events = [];
  function* values() {
    try {
      yield 1;
      yield 2;
    } finally {
      events.push('closed');
    }
  }
  const iterator = values();

  iterator.next();
  assert.deepEqual(iterator.return('done'), { value: 'done', done: true });
  assert.deepEqual(events, ['closed']);
});

test('generator 与 iterator helper 都是单次游标', () => {
  const iterator = Iterator.from([1, 2]).map((value) => value * 2);

  assert.deepEqual(iterator.toArray(), [2, 4]);
  assert.deepEqual(iterator.toArray(), []);
});

