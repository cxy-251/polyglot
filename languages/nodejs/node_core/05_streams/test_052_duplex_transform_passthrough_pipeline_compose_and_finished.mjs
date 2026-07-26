// polyglot-covers:
// - nodejs.core.stream-duplex-independent-readable-writable-sides
// - nodejs.core.stream-duplex-pair-and-half-open
// - nodejs.core.stream-transform-custom-transform-and-flush
// - nodejs.core.stream-pass-through
// - nodejs.core.stream-pipeline-callback-and-promises
// - nodejs.core.stream-compose
// - nodejs.core.stream-finished-and-cleanup
// - nodejs.core.stream-pipeline-error-destruction

import assert from 'node:assert/strict';
import test from 'node:test';

import { once } from 'node:events';
import {
  Duplex,
  PassThrough,
  Readable,
  Transform,
  Writable,
  compose,
  duplexPair,
  finished as finishedCallback,
  pipeline as pipelineCallback,
} from 'node:stream';
import { finished, pipeline } from 'node:stream/promises';
import { promisify } from 'node:util';

test('Duplex 的 readable/writable 状态和 highWaterMark 相互独立', async () => {
  const writes = [];
  const stream = new Duplex({
    readableHighWaterMark: 4,
    read() {
      this.push('output');
      this.push(null);
    },
    writableHighWaterMark: 8,
    write(chunk, encoding, callback) {
      writes.push(chunk.toString());
      callback();
    },
  });

  stream.end('input');
  assert.deepEqual(await stream.toArray(), [Buffer.from('output')]);
  await finished(stream);

  assert.deepEqual(writes, ['input']);
  assert.equal(stream.readableHighWaterMark, 4);
  assert.equal(stream.writableHighWaterMark, 8);
});

test('duplexPair 创建交叉连接的双工端点', async () => {
  const [left, right] = duplexPair();

  const rightReadable = once(right, 'readable');
  left.write('from left');
  await rightReadable;
  assert.equal(right.read().toString(), 'from left');

  const leftReadable = once(left, 'readable');
  right.write('from right');
  await leftReadable;
  assert.equal(left.read().toString(), 'from right');

  left.end();
  right.end();
  // Readable 的 end 事件只有在数据被消费时才触发；finished 等待双工两侧，
  // 因此这里显式 resume 以排空 EOF，而不是留下永远 paused 的 readable 侧。
  left.resume();
  right.resume();
  await Promise.all([finished(left), finished(right)]);
});

test('allowHalfOpen false 在 readable 结束后自动结束 writable 侧', async () => {
  const stream = new Duplex({
    allowHalfOpen: false,
    read() {
      this.push(null);
    },
    write(chunk, encoding, callback) {
      callback();
    },
  });

  stream.resume();
  await once(stream, 'finish');
  assert.equal(stream.readableEnded, true);
  assert.equal(stream.writableEnded, true);
});

test('Transform 的 _transform 可输出零到多个 chunk，_flush 添加尾部', async () => {
  const transform = new Transform({
    transform(chunk, encoding, callback) {
      const words = chunk.toString().split(',');
      for (const word of words) {
        if (word) this.push(word.toUpperCase());
      }
      callback();
    },
    flush(callback) {
      this.push('!');
      callback();
    },
  });

  Readable.from(['one,two,', 'three']).pipe(transform);
  const chunks = await transform.toArray();
  assert.equal(Buffer.concat(chunks).toString(), 'ONETWOTHREE!');
});

test('objectMode Transform 可改变对象形状', async () => {
  const transform = new Transform({
    objectMode: true,
    transform(record, encoding, callback) {
      callback(null, { ...record, normalized: record.name.toLowerCase() });
    },
  });

  Readable.from([{ name: 'ADA' }, { name: 'GRACE' }]).pipe(transform);
  assert.deepEqual(await transform.toArray(), [
    { name: 'ADA', normalized: 'ada' },
    { name: 'GRACE', normalized: 'grace' },
  ]);
});

test('PassThrough 不改变数据，适合观察、分支或测试边界', async () => {
  const pass = new PassThrough();
  const observed = [];
  pass.on('data', (chunk) => observed.push(Buffer.from(chunk)));

  pass.end('payload');
  await once(pass, 'end');
  assert.equal(Buffer.concat(observed).toString(), 'payload');
  assert.equal(pass.readableEnded, true);
  assert.equal(pass.writableFinished, true);
});

test('Promise pipeline 连接 iterable、async generator 和 Writable', async () => {
  const output = [];
  async function* multiply(source) {
    for await (const value of source) {
      yield value * 2;
    }
  }
  const destination = new Writable({
    objectMode: true,
    write(value, encoding, callback) {
      output.push(value);
      callback();
    },
  });

  await pipeline([1, 2, 3], multiply, destination);
  assert.deepEqual(output, [2, 4, 6]);
});

test('callback pipeline 可 promisify，错误会销毁参与流', async () => {
  const pipelineAsync = promisify(pipelineCallback);
  const failure = new Error('transform failed');
  const source = Readable.from(['value']);
  const transform = new Transform({
    transform(chunk, encoding, callback) {
      callback(failure);
    },
  });
  const destination = new PassThrough();

  await assert.rejects(
    pipelineAsync(source, transform, destination),
    (error) => error === failure,
  );
  assert.equal(source.destroyed, true);
  assert.equal(transform.destroyed, true);
  assert.equal(destination.destroyed, true);
});

test('compose 把多个 transform 组合成一个 Duplex', async () => {
  const uppercase = new Transform({
    transform(chunk, encoding, callback) {
      callback(null, chunk.toString().toUpperCase());
    },
  });
  const brackets = async function* (source) {
    for await (const chunk of source) {
      yield `[${chunk}]`;
    }
  };
  const combined = compose(uppercase, brackets);

  combined.end('value');
  assert.equal((await combined.toArray()).join(''), '[VALUE]');
});

test('finished Promise 等待完整生命周期，callback 版本返回清理函数', async () => {
  const stream = new PassThrough();
  const callbackEvents = [];
  const cleanup = finishedCallback(stream, (error) => callbackEvents.push(error));
  const pending = finished(stream, { cleanup: true });

  stream.resume();
  stream.end('value');
  await pending;
  assert.deepEqual(callbackEvents, [undefined]);
  assert.equal(typeof cleanup, 'function');
  cleanup();
});
