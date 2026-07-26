// polyglot-covers:
// - nodejs.language.promise-constructor-and-settlement
// - nodejs.language.promise-resolution-and-thenables
// - nodejs.language.promise-chaining-and-error-propagation
// - nodejs.language.promise-finally
// - nodejs.language.promise-all-and-all-settled
// - nodejs.language.promise-race-and-any
// - nodejs.language.promise-with-resolvers
// - nodejs.language.promise-try

import assert from 'node:assert/strict';
import test from 'node:test';

test('Promise executor 同步执行，reaction 总在后续 job 执行', async () => {
  const events = [];
  const promise = new Promise((resolve) => {
    events.push('executor');
    resolve('value');
    events.push('after resolve');
  });

  promise.then((value) => events.push(`then:${value}`));
  events.push('synchronous end');

  assert.deepEqual(events, ['executor', 'after resolve', 'synchronous end']);
  await promise;
  await Promise.resolve();
  assert.deepEqual(events, [
    'executor',
    'after resolve',
    'synchronous end',
    'then:value',
  ]);
});

test('首次 settle 获胜，之后 resolve/reject 不会改变状态', async () => {
  const fulfilled = new Promise((resolve, reject) => {
    resolve(1);
    reject(new Error('ignored'));
    resolve(2);
  });
  assert.equal(await fulfilled, 1);

  const error = new Error('first');
  const rejected = new Promise((resolve, reject) => {
    reject(error);
    resolve('ignored');
  });
  await assert.rejects(rejected, (actual) => actual === error);
});

test('resolve 会吸收 Promise 和普通 thenable 的最终状态', async () => {
  const thenable = {
    then(resolve) {
      resolve('from thenable');
    },
  };

  assert.equal(await Promise.resolve(thenable), 'from thenable');

  const original = Promise.resolve(7);
  assert.equal(Promise.resolve(original), original);
  assert.equal(await Promise.resolve(Promise.resolve(original)), 7);
});

test('then 返回新 Promise，并吸收返回值、异常或另一个 Promise', async () => {
  const original = Promise.resolve(2);
  const chained = original
    .then((value) => value * 3)
    .then((value) => Promise.resolve(value + 1));

  assert.notEqual(chained, original);
  assert.equal(await chained, 7);

  const failure = original.then(() => {
    throw new RangeError('broken');
  });
  await assert.rejects(failure, {
    message: 'broken',
    name: 'RangeError',
  });
});

test('catch 是 then(undefined, handler) 的便捷形式并可恢复链', async () => {
  const result = await Promise.reject(new Error('failure'))
    .catch((error) => `recovered:${error.message}`)
    .then((value) => value.toUpperCase());

  assert.equal(result, 'RECOVERED:FAILURE');

  const rethrown = Promise.reject(new Error('first')).catch((error) => {
    throw new Error('wrapped', { cause: error });
  });
  await assert.rejects(rethrown, (error) => {
    assert.equal(error.message, 'wrapped');
    assert.equal(error.cause.message, 'first');
    return true;
  });
});

test('finally 不接收结果，通常透明传递原状态', async () => {
  const events = [];
  const fulfilled = Promise.resolve(7).finally(() => {
    events.push('fulfilled cleanup');
    return 99;
  });
  assert.equal(await fulfilled, 7);

  const original = new Error('original');
  const rejected = Promise.reject(original).finally(() => {
    events.push('rejected cleanup');
  });
  await assert.rejects(rejected, (error) => error === original);
  assert.deepEqual(events, ['fulfilled cleanup', 'rejected cleanup']);

  const overridden = Promise.resolve('value').finally(() => {
    throw new Error('cleanup failed');
  });
  await assert.rejects(overridden, /cleanup failed/);
});

test('Promise.all 保持输入顺序并在首个拒绝时拒绝', async () => {
  const values = await Promise.all([
    Promise.resolve('first'),
    'second',
    Promise.resolve('third'),
  ]);
  assert.deepEqual(values, ['first', 'second', 'third']);

  const failure = new Error('failed');
  await assert.rejects(
    Promise.all([Promise.resolve(1), Promise.reject(failure)]),
    (error) => error === failure,
  );
  assert.deepEqual(await Promise.all([]), []);
});

test('allSettled 等待全部输入并用判别字段保存结果', async () => {
  const failure = new Error('failed');
  const results = await Promise.allSettled([
    Promise.resolve(1),
    Promise.reject(failure),
  ]);

  assert.deepEqual(results, [
    { status: 'fulfilled', value: 1 },
    { reason: failure, status: 'rejected' },
  ]);
});

test('race 采用首个 settled，空输入永远保持 pending', async () => {
  assert.equal(await Promise.race([Promise.resolve('first'), 'second']), 'first');

  const sentinel = Symbol('sentinel');
  const observed = await Promise.race([
    Promise.race([]),
    Promise.resolve(sentinel),
  ]);
  assert.equal(observed, sentinel);

  // race([]) 没有任何输入能够 settle；真实程序应避免把空集合无意传入超时/竞速逻辑。
});

test('Promise.any 采用首个 fulfilled，全部拒绝时产生 AggregateError', async () => {
  const firstError = new Error('first');
  const secondError = new Error('second');

  assert.equal(await Promise.any([
    Promise.reject(firstError),
    Promise.resolve('success'),
  ]), 'success');

  await assert.rejects(
    Promise.any([Promise.reject(firstError), Promise.reject(secondError)]),
    (error) => {
      assert.equal(error instanceof AggregateError, true);
      assert.deepEqual(error.errors, [firstError, secondError]);
      return true;
    },
  );
});

test('withResolvers 把能力函数与 Promise 一起返回', {
  skip: typeof Promise.withResolvers !== 'function',
}, async () => {
  const { promise, resolve, reject } = Promise.withResolvers();

  assert.equal(typeof resolve, 'function');
  assert.equal(typeof reject, 'function');
  resolve(42);
  assert.equal(await promise, 42);
});

test('Promise.try 把同步抛错和异步返回统一成 Promise', {
  skip: typeof Promise.try !== 'function',
}, async () => {
  assert.equal(await Promise.try((left, right) => left + right, 2, 3), 5);

  await assert.rejects(
    Promise.try(() => {
      throw new TypeError('invalid');
    }),
    TypeError,
  );
});
