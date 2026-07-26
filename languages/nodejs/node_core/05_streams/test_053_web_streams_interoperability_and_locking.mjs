// polyglot-covers:
// - nodejs.core.stream-web-readable-from-web-and-locking
// - nodejs.core.stream-web-readable-to-web-and-cancellation
// - nodejs.core.stream-web-writable-from-web
// - nodejs.core.stream-web-writable-to-web-and-writer-lock
// - nodejs.core.stream-web-duplex-from-web
// - nodejs.core.stream-web-duplex-to-web
// - nodejs.core.stream-web-pipeline-interoperability
// - nodejs.core.stream-readable-is-disturbed

import assert from 'node:assert/strict';
import test from 'node:test';

import { once } from 'node:events';
import { Duplex, Readable, Transform, Writable } from 'node:stream';
import { finished, pipeline } from 'node:stream/promises';
import {
  ReadableStream,
  TransformStream,
  WritableStream,
} from 'node:stream/web';

const encoder = new TextEncoder();
const decoder = new TextDecoder();

test('Readable.fromWeb 取得 Web 流的 reader 锁并把 Uint8Array 转为 Buffer', async () => {
  const webReadable = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode('hello '));
      controller.enqueue(encoder.encode('web stream'));
      controller.close();
    },
  });

  assert.equal(webReadable.locked, false);
  assert.equal(Readable.isDisturbed(webReadable), false);

  const nodeReadable = Readable.fromWeb(webReadable);
  assert.equal(webReadable.locked, true);
  await assert.rejects(
    Promise.resolve().then(() => webReadable.getReader()),
    (error) => error instanceof TypeError && error.code === 'ERR_INVALID_STATE',
  );

  const chunks = await nodeReadable.toArray();
  assert.ok(chunks.every(Buffer.isBuffer));
  assert.equal(Buffer.concat(chunks).toString(), 'hello web stream');
  assert.equal(Readable.isDisturbed(webReadable), true);
});

test('Readable.toWeb 的 reader.cancel 会销毁底层 Node Readable', async () => {
  let pushed = false;
  const nodeReadable = new Readable({
    read() {
      if (!pushed) {
        pushed = true;
        this.push('first');
      }
    },
  });
  const errors = [];
  nodeReadable.on('error', (error) => errors.push(error));
  const closed = new Promise((resolve) => nodeReadable.once('close', resolve));
  const webReadable = Readable.toWeb(nodeReadable);
  const reader = webReadable.getReader();

  const first = await reader.read();
  assert.equal(decoder.decode(first.value), 'first');
  const reason = new Error('consumer stopped');
  await reader.cancel(reason);
  await closed;

  assert.equal(nodeReadable.destroyed, true);
  assert.equal(Readable.isDisturbed(nodeReadable), true);
  // 取消原因会用于 destroy；应用若监听 error，应按流契约处理它，不能假设静默关闭。
  assert.deepEqual(errors, [reason]);
});

test('Writable.fromWeb 把 Node 写入桥接给 Web sink，并在 end 时 close', async () => {
  const observed = [];
  let closeCalls = 0;
  const webWritable = new WritableStream({
    write(chunk) {
      observed.push(decoder.decode(chunk));
    },
    close() {
      closeCalls += 1;
    },
  });
  const nodeWritable = Writable.fromWeb(webWritable);

  nodeWritable.write('first');
  nodeWritable.end('second');
  await finished(nodeWritable);

  assert.deepEqual(observed, ['first', 'second']);
  assert.equal(closeCalls, 1);
  assert.equal(webWritable.locked, true);
});

test('Writable.toWeb 通过 writer 写入 Node sink，close 对应 Node end', async () => {
  const observed = [];
  let finalCalls = 0;
  const nodeWritable = new Writable({
    write(chunk, encoding, callback) {
      observed.push(chunk.toString());
      callback();
    },
    final(callback) {
      finalCalls += 1;
      callback();
    },
  });
  const webWritable = Writable.toWeb(nodeWritable);
  const writer = webWritable.getWriter();

  assert.equal(webWritable.locked, true);
  await writer.write(encoder.encode('payload'));
  await writer.close();
  await finished(nodeWritable);
  writer.releaseLock();

  assert.deepEqual(observed, ['payload']);
  assert.equal(finalCalls, 1);
  assert.equal(nodeWritable.writableFinished, true);
  assert.equal(webWritable.locked, false);
});

test('Duplex.toWeb 把 Transform 暴露成 readable/writable 对', async () => {
  const transform = new Transform({
    transform(chunk, encoding, callback) {
      callback(null, chunk.toString().toUpperCase());
    },
  });
  const pair = Duplex.toWeb(transform);
  const reader = pair.readable.getReader();
  const writer = pair.writable.getWriter();

  // 先启动读取，避免大数据时 writer 因 readable 侧背压而一直等待。
  const firstRead = reader.read();
  await writer.write(encoder.encode('duplex'));
  assert.equal(decoder.decode((await firstRead).value), 'DUPLEX');
  await writer.close();
  assert.deepEqual(await reader.read(), { value: undefined, done: true });
  await finished(transform);
});

test('Duplex.fromWeb 把 Web readable/writable 对适配成 Node 双工流', async () => {
  const webTransform = new TransformStream({
    transform(chunk, controller) {
      controller.enqueue(`${chunk}!`);
    },
  });
  const duplex = Duplex.fromWeb(webTransform, { objectMode: true });

  duplex.end('hello');
  assert.deepEqual(await duplex.toArray(), ['hello!']);
  await finished(duplex);

  assert.equal(webTransform.readable.locked, true);
  assert.equal(webTransform.writable.locked, true);
});

test('Promise pipeline 可以直接串联 Node 流与 Web Transform/WritableStream', async () => {
  const output = [];
  const double = new TransformStream({
    transform(value, controller) {
      controller.enqueue(value * 2);
    },
  });
  const destination = new WritableStream({
    write(value) {
      output.push(value);
    },
  });

  await pipeline(Readable.from([1, 2, 3]), double, destination);
  assert.deepEqual(output, [2, 4, 6]);
});

test('消费或取消都会把 Web Readable 标记为 disturbed', async () => {
  const consumed = new ReadableStream({
    start(controller) {
      controller.enqueue('value');
      controller.close();
    },
  });
  const consumedReader = consumed.getReader();
  assert.equal(Readable.isDisturbed(consumed), false);
  await consumedReader.read();
  assert.equal(Readable.isDisturbed(consumed), true);

  const cancelled = new ReadableStream();
  assert.equal(Readable.isDisturbed(cancelled), false);
  await cancelled.cancel('unused');
  assert.equal(Readable.isDisturbed(cancelled), true);
});
