// polyglot-covers:
// - nodejs.language.shared-array-buffer
// - nodejs.language.atomics-load-store-and-arithmetic
// - nodejs.language.atomics-exchange-and-compare-exchange
// - nodejs.language.atomics-wait-notify-and-wait-async
// - nodejs.language.atomics-bigint-typed-arrays
// - nodejs.language.atomics-lock-free-capability

import assert from 'node:assert/strict';
import test from 'node:test';

test('多个 TypedArray 视图可以共享 SharedArrayBuffer 内存', () => {
  const buffer = new SharedArrayBuffer(8);
  const first = new Int32Array(buffer);
  const second = new Int32Array(buffer);

  first[0] = 7;
  second[1] = 9;

  assert.equal(first.buffer, buffer);
  assert.equal(second.buffer, buffer);
  assert.deepEqual([...first], [7, 9]);
  assert.equal(buffer.byteLength, 8);

  // 普通读写会看到同一存储，但跨 agent 的同步和可见性必须通过 Atomics 或更高层协议建立。
});

test('Atomics.load/store 提供顺序一致的整数读写', () => {
  const values = new Int32Array(new SharedArrayBuffer(8));

  assert.equal(Atomics.store(values, 0, 42), 42);
  assert.equal(Atomics.load(values, 0), 42);

  assert.throws(() => Atomics.load(values, 2), RangeError);
  assert.throws(
    () => Atomics.load(new Float64Array(new SharedArrayBuffer(8)), 0),
    TypeError,
  );
});

test('原子算术返回修改前的值，并把结果写回视图', () => {
  const values = new Int32Array(new SharedArrayBuffer(4));
  values[0] = 10;

  assert.equal(Atomics.add(values, 0, 5), 10);
  assert.equal(Atomics.load(values, 0), 15);
  assert.equal(Atomics.sub(values, 0, 3), 15);
  assert.equal(Atomics.load(values, 0), 12);
  assert.equal(Atomics.and(values, 0, 0b1010), 12);
  assert.equal(Atomics.load(values, 0), 0b1000);
  assert.equal(Atomics.or(values, 0, 0b0011), 0b1000);
  assert.equal(Atomics.xor(values, 0, 0b0101), 0b1011);
  assert.equal(Atomics.load(values, 0), 0b1110);
});

test('exchange 无条件替换，compareExchange 只在期望值匹配时替换', () => {
  const values = new Int32Array(new SharedArrayBuffer(4));
  values[0] = 7;

  assert.equal(Atomics.exchange(values, 0, 10), 7);
  assert.equal(values[0], 10);

  assert.equal(Atomics.compareExchange(values, 0, 9, 20), 10);
  assert.equal(values[0], 10);
  assert.equal(Atomics.compareExchange(values, 0, 10, 20), 10);
  assert.equal(values[0], 20);

  // compareExchange 是构建无锁算法的原语；真实循环还必须处理竞争、进度与溢出。
});

test('waitAsync 在当前值不匹配时同步返回 not-equal', async () => {
  const values = new Int32Array(new SharedArrayBuffer(4));
  values[0] = 1;

  const result = Atomics.waitAsync(values, 0, 2);
  assert.deepEqual(result, {
    async: false,
    value: 'not-equal',
  });
  assert.equal(await result.value, 'not-equal');
});

test('waitAsync 可由同一进程后续 notify 唤醒且不阻塞事件循环', async () => {
  const values = new Int32Array(new SharedArrayBuffer(4));
  const waiting = Atomics.waitAsync(values, 0, 0);

  assert.equal(waiting.async, true);
  assert.equal(waiting.value instanceof Promise, true);
  assert.equal(Atomics.notify(values, 0, 1), 1);
  assert.equal(await waiting.value, 'ok');

  assert.equal(Atomics.notify(values, 0), 0);
});

test('BigInt64Array 和 BigUint64Array 支持对应 BigInt 原子操作', () => {
  const signed = new BigInt64Array(new SharedArrayBuffer(8));

  assert.equal(Atomics.store(signed, 0, 10n), 10n);
  assert.equal(Atomics.add(signed, 0, 5n), 10n);
  assert.equal(Atomics.load(signed, 0), 15n);
  assert.throws(() => Atomics.store(signed, 0, 1), TypeError);

  const unsigned = new BigUint64Array(new SharedArrayBuffer(8));
  Atomics.store(unsigned, 0, -1n);
  assert.equal(Atomics.load(unsigned, 0), 2n ** 64n - 1n);
});

test('isLockFree 报告实现对给定字节宽度是否原生无锁', () => {
  assert.equal(Atomics.isLockFree(1), true);
  assert.equal(Atomics.isLockFree(2), true);
  assert.equal(Atomics.isLockFree(4), true);
  assert.equal(typeof Atomics.isLockFree(8), 'boolean');
  assert.equal(Atomics.isLockFree(3), false);

  // 8 字节结果允许依赖平台；算法不能把 isLockFree 当成数据正确性的条件。
});
