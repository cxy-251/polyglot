// 流、缓冲与背压。
// 共同问题：文本与字节流如何区分；游标和刷新何时生效；生产者如何知道消费者暂时跟不上；
// 同步流与事件驱动流是否采用同一种背压协议。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: streaming_buffering_and_backpressure
// polyglot-related: languages/nodejs/node_core/05_streams/
// polyglot-related+: test_050_readable_stream_modes_async_iteration_and_functional_helpers.mjs

import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { Readable, Writable } from 'node:stream';

test('Readable 异步迭代按块消费数据', async () => {
  const chunks = [];

  for await (const chunk of Readable.from([Buffer.from('a'), Buffer.from('b')])) {
    chunks.push(chunk.toString());
  }

  assert.deepEqual(chunks, ['a', 'b']);
});

test('setEncoding 将后续读取从 Buffer 解码成字符串', async () => {
  const readable = Readable.from([Buffer.from('你好')]).setEncoding('utf8');
  const chunks = [];

  for await (const chunk of readable) {
    chunks.push(chunk);
  }

  assert.deepEqual(chunks, ['你好']);
});

test('write 返回 false 时生产者等待 drain', async () => {
  let releaseWrite;
  const writable = new Writable({
    highWaterMark: 1,
    write(_chunk, _encoding, callback) {
      releaseWrite = callback;
    },
  });

  const accepted = writable.write(Buffer.from('value'));
  assert.equal(accepted, false);
  const drained = once(writable, 'drain');
  releaseWrite();
  await drained;
  writable.end();
  await once(writable, 'finish');
});

test('忽略背压信号不会自动丢弃已经写入的数据', async () => {
  const chunks = [];
  const callbacks = [];
  const writable = new Writable({
    highWaterMark: 1,
    write(chunk, _encoding, callback) {
      chunks.push(chunk.toString());
      callbacks.push(callback);
    },
  });

  assert.equal(writable.write('a'), false);
  assert.equal(writable.write('b'), false);
  callbacks.shift()();
  callbacks.shift()();
  const finished = once(writable, 'finish');
  writable.end();
  await finished;

  assert.deepEqual(chunks, ['a', 'b']);

  // false 是暂停生产的建议；忽略它会继续累积缓冲，不会替调用方丢弃数据或抛出同步异常。
});
