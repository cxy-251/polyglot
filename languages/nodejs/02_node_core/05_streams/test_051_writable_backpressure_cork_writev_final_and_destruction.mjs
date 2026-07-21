// polyglot-covers:
// - nodejs.core.stream-writable-custom-write-final-and-destroy
// - nodejs.core.stream-writable-backpressure-and-drain
// - nodejs.core.stream-writable-object-mode-high-water-mark
// - nodejs.core.stream-writable-cork-uncork-and-writev
// - nodejs.core.stream-writable-end-finish-close-and-errors
// - nodejs.core.stream-writable-destroy-and-error-propagation
// - nodejs.core.stream-writable-symbol-async-dispose

import assert from 'node:assert/strict';
import test from 'node:test';

import { once } from 'node:events';
import { Writable } from 'node:stream';

function waitForClose(stream) {
  // events.once(stream, 'close') 会特别监听 error 并先 reject；当案例本来就期望
  // error -> close 时，只监听 close 才能同时核对完整事件顺序。
  return new Promise((resolve) => stream.once('close', resolve));
}

class RecordingWritable extends Writable {
  constructor(options = {}) {
    super(options);
    this.events = [];
  }

  _write(chunk, encoding, callback) {
    this.events.push(`write:${chunk.toString()}:${encoding}`);
    callback();
  }

  _final(callback) {
    this.events.push('final');
    callback();
  }

  _destroy(error, callback) {
    this.events.push(`destroy:${error?.message ?? 'none'}`);
    callback(error);
  }
}

test('write 把数据交给 _write，end 后依次触发 final、finish 和 close', async () => {
  const stream = new RecordingWritable();
  const lifecycle = [];
  stream.on('finish', () => lifecycle.push('finish'));
  stream.on('close', () => lifecycle.push('close'));

  assert.equal(stream.write('first'), true);
  stream.end('last');
  await once(stream, 'close');

  assert.deepEqual(stream.events, [
    'write:first:buffer',
    'write:last:buffer',
    'final',
    'destroy:none',
  ]);
  assert.deepEqual(lifecycle, ['finish', 'close']);
  assert.equal(stream.writableFinished, true);
  assert.equal(stream.destroyed, true);
});

test('write 返回 false 表示生产者应等待 drain 再继续', async () => {
  const callbacks = [];
  const chunks = [];
  const stream = new Writable({
    highWaterMark: 3,
    write(chunk, encoding, callback) {
      chunks.push(chunk.toString());
      callbacks.push(callback);
    },
  });

  assert.equal(stream.write('ab'), true);
  assert.equal(stream.write('cd'), false);
  assert.equal(stream.writableNeedDrain, true);
  const drained = once(stream, 'drain');

  callbacks.shift()();
  // Writable 只有在前一个 _write callback 完成后才会把下一块交给 _write。
  // 因此必须先释放第一块，再取得刚进入 callbacks 队列的第二个 callback。
  assert.equal(callbacks.length, 1);
  callbacks.shift()();
  await drained;
  assert.equal(stream.writableNeedDrain, false);
  assert.deepEqual(chunks, ['ab', 'cd']);

  stream.end();
  await once(stream, 'close');
});

test('objectMode 的 highWaterMark 按对象数量而不是字节计算', async () => {
  const callbacks = [];
  const stream = new Writable({
    highWaterMark: 2,
    objectMode: true,
    write(value, encoding, callback) {
      assert.equal(typeof value, 'object');
      callbacks.push(callback);
    },
  });

  assert.equal(stream.write({ id: 1 }), true);
  assert.equal(stream.write({ id: 2 }), false);
  assert.equal(stream.writableLength, 2);
  const drained = once(stream, 'drain');
  callbacks.shift()();
  assert.equal(callbacks.length, 1);
  callbacks.shift()();
  await drained;
  stream.end();
  await waitForClose(stream);
});

test('cork 缓冲写入，_writev 可批量处理多个 chunk', async () => {
  const batches = [];
  const stream = new Writable({
    write(chunk, encoding, callback) {
      batches.push([chunk.toString()]);
      callback();
    },
    writev(chunks, callback) {
      batches.push(chunks.map(({ chunk }) => chunk.toString()));
      callback();
    },
  });

  stream.cork();
  stream.write('a');
  stream.write('b');
  stream.write('c');
  assert.deepEqual(batches, []);
  stream.uncork();
  stream.end('d');
  await waitForClose(stream);

  assert.deepEqual(batches, [['a', 'b', 'c'], ['d']]);
});

test('嵌套 cork 需要相同次数 uncork，end 会强制冲刷剩余数据', async () => {
  const chunks = [];
  const stream = new Writable({
    write(chunk, encoding, callback) {
      chunks.push(chunk.toString());
      callback();
    },
  });

  stream.cork();
  stream.cork();
  stream.write('value');
  stream.uncork();
  assert.deepEqual(chunks, []);
  stream.end();
  await waitForClose(stream);
  assert.deepEqual(chunks, ['value']);
});

test('decodeStrings false 让字符串保持字符串并保留声明 encoding', async () => {
  const observed = [];
  const stream = new Writable({
    decodeStrings: false,
    defaultEncoding: 'utf8',
    write(chunk, encoding, callback) {
      observed.push({ chunk, encoding });
      callback();
    },
  });

  stream.end('中文');
  await once(stream, 'close');
  assert.deepEqual(observed, [{ chunk: '中文', encoding: 'utf8' }]);
});

test('_write 的错误触发 error 并阻止 finish，随后 close', async () => {
  const failure = new Error('write failed');
  const stream = new Writable({
    write(chunk, encoding, callback) {
      callback(failure);
    },
  });
  const events = [];
  stream.on('finish', () => events.push('finish'));
  stream.on('error', (error) => events.push(`error:${error.message}`));
  stream.on('close', () => events.push('close'));

  const closed = waitForClose(stream);
  stream.end('value');
  await closed;
  assert.deepEqual(events, ['error:write failed', 'close']);
  assert.equal(stream.writableFinished, false);
  assert.equal(stream.destroyed, true);
});

test('destroy(error) 只调用一次 _destroy，并发出 error 后 close', async () => {
  const stream = new RecordingWritable();
  const failure = new Error('cancelled');
  const errors = [];
  stream.on('error', (error) => errors.push(error));

  const closed = waitForClose(stream);
  stream.destroy(failure);
  stream.destroy(new Error('ignored'));
  await closed;

  assert.deepEqual(errors, [failure]);
  assert.deepEqual(stream.events, ['destroy:cancelled']);
});

test('end 后 write 通过 callback 报 ERR_STREAM_WRITE_AFTER_END', async () => {
  const stream = new Writable({
    write(chunk, encoding, callback) {
      callback();
    },
  });
  stream.on('error', () => undefined);
  const closed = waitForClose(stream);
  stream.end();

  const error = await new Promise((resolve) => {
    stream.write('late', (actual) => resolve(actual));
  });
  assert.equal(error.code, 'ERR_STREAM_WRITE_AFTER_END');
  await closed;
});

test('Symbol.asyncDispose 用 AbortError destroy 并等待流关闭', async () => {
  const stream = new Writable({
    write(chunk, encoding, callback) {
      callback();
    },
  });
  stream.on('error', () => undefined);

  await stream[Symbol.asyncDispose]();
  assert.equal(stream.destroyed, true);
  assert.equal(stream.closed, true);
});
