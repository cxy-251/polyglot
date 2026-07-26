// polyglot-covers:
// - nodejs.core.stream-consumers-array-buffer-blob-buffer-json-and-text
// - nodejs.core.stream-consumers-json-errors
// - nodejs.core.stream-state-is-readable-writable-and-errored
// - nodejs.core.stream-add-abort-signal
// - nodejs.core.stream-default-high-water-mark
// - nodejs.core.stream-duplex-from-sources-and-functions
// - nodejs.core.stream-readable-unshift-parser-lookahead
// - nodejs.core.stream-readable-read-zero
// - nodejs.core.stream-readable-wrap-legacy-source

import assert from 'node:assert/strict';
import test from 'node:test';

import { EventEmitter, once } from 'node:events';
import {
  Duplex,
  Readable,
  Writable,
  addAbortSignal,
  getDefaultHighWaterMark,
  isErrored,
  isReadable,
  isWritable,
  setDefaultHighWaterMark,
} from 'node:stream';
import {
  arrayBuffer,
  blob,
  buffer,
  json,
  text,
} from 'node:stream/consumers';
import { finished } from 'node:stream/promises';

test('stream/consumers 把完整流收集为 ArrayBuffer、Blob、Buffer 或文本', async () => {
  const bytes = await arrayBuffer(Readable.from([
    Buffer.from('array'),
    Buffer.from(' buffer'),
  ]));
  assert.equal(Buffer.from(bytes).toString(), 'array buffer');

  const collectedBlob = await blob(Readable.from(['blob data']));
  assert.ok(collectedBlob instanceof Blob);
  assert.equal(await collectedBlob.text(), 'blob data');

  const collectedBuffer = await buffer(Readable.from(['buffer data']));
  assert.ok(Buffer.isBuffer(collectedBuffer));
  assert.equal(collectedBuffer.toString(), 'buffer data');

  // consumers 也接受 AsyncIterable，不局限于 Node Readable 实例。
  async function* chunks() {
    yield 'async ';
    yield 'iterable';
  }
  assert.equal(await text(chunks()), 'async iterable');
});

test('json consumer 先收集完整内容再 JSON.parse，非法输入拒绝 SyntaxError', async () => {
  const value = await json(Readable.from(['{"name":', '"Ada","active":true}']));
  assert.deepEqual(value, { name: 'Ada', active: true });

  await assert.rejects(
    json(Readable.from(['{"incomplete":'])),
    SyntaxError,
  );
  // 它不是增量 JSON 解析器；超大或不可信正文仍需在上游限制大小。
});

test('isReadable/isWritable/isErrored 用统一接口探测 Node 流状态', async () => {
  const readable = Readable.from(['value']);
  const writable = new Writable({
    write(chunk, encoding, callback) {
      callback();
    },
  });

  assert.equal(isReadable(readable), true);
  assert.equal(isWritable(readable), null);
  assert.equal(isReadable(writable), null);
  assert.equal(isWritable(writable), true);
  assert.equal(isErrored(readable), false);
  assert.equal(isReadable({}), null);

  await readable.toArray();
  writable.end();
  await finished(writable);
  assert.equal(isReadable(readable), false);
  assert.equal(isWritable(writable), false);

  const failure = new Error('broken stream');
  const failed = new Readable({
    read() {
      this.destroy(failure);
    },
  });
  failed.on('error', () => undefined);
  const failedClosed = new Promise((resolve) => failed.once('close', resolve));
  failed.resume();
  await failedClosed;
  assert.equal(isErrored(failed), true);
  assert.equal(failed.errored, failure);
});

test('addAbortSignal 在 signal abort 时用 AbortError 销毁 Node 流', async () => {
  const controller = new AbortController();
  const stream = new Readable({
    read() {},
  });
  const errors = [];
  stream.on('error', (error) => errors.push(error));
  const closed = new Promise((resolve) => stream.once('close', resolve));

  assert.equal(addAbortSignal(controller.signal, stream), stream);
  controller.abort(new Error('caller cancelled'));
  await closed;

  assert.equal(stream.destroyed, true);
  assert.equal(isErrored(stream), true);
  assert.equal(errors.length, 1);
  assert.equal(errors[0].name, 'AbortError');
  assert.equal(errors[0].code, 'ABORT_ERR');
  assert.equal(errors[0].cause, controller.signal.reason);
});

test('默认 highWaterMark 可按字节模式与 objectMode 分别配置并恢复', () => {
  const previousBytes = getDefaultHighWaterMark(false);
  const previousObjects = getDefaultHighWaterMark(true);

  try {
    setDefaultHighWaterMark(false, 12_345);
    setDefaultHighWaterMark(true, 7);

    const byteReadable = new Readable({ read() {} });
    const byteWritable = new Writable({
      write(chunk, encoding, callback) {
        callback();
      },
    });
    const objectReadable = new Readable({ objectMode: true, read() {} });

    assert.equal(byteReadable.readableHighWaterMark, 12_345);
    assert.equal(byteWritable.writableHighWaterMark, 12_345);
    assert.equal(objectReadable.readableHighWaterMark, 7);
    // 显式选项优先于进程级默认值。
    assert.equal(new Readable({ highWaterMark: 99, read() {} }).readableHighWaterMark, 99);

    byteReadable.destroy();
    byteWritable.destroy();
    objectReadable.destroy();
  } finally {
    // 这是进程级可变状态；测试或库代码修改后必须恢复，避免污染后续流。
    setDefaultHighWaterMark(false, previousBytes);
    setDefaultHighWaterMark(true, previousObjects);
  }
});

test('Duplex.from 可把 iterable 和 async generator function 变成统一流接口', async () => {
  const readableOnly = Duplex.from(['a', 'b']);
  assert.equal(readableOnly.readable, true);
  assert.equal(readableOnly.writable, false);
  assert.deepEqual(await readableOnly.toArray(), ['a', 'b']);

  const transform = Duplex.from(async function* double(source) {
    for await (const value of source) {
      yield value * 2;
    }
  });
  transform.end(3);
  assert.deepEqual(await transform.toArray(), [6]);

  const received = [];
  const writableOnly = Duplex.from(async (source) => {
    for await (const value of source) {
      received.push(value);
    }
  });
  assert.equal(writableOnly.readable, false);
  writableOnly.end('sink value');
  await finished(writableOnly);
  // 函数适配器通过 async iterable 传值，默认保留字符串，不套用普通 _write 的
  // decodeStrings -> Buffer 规则。
  assert.deepEqual(received, ['sink value']);
});

test('unshift 把解析器多读的字节放回队首，供下一轮消费', async () => {
  const stream = Readable.from([Buffer.from('HEAD\nBODY')], { objectMode: false });
  const headerChunks = [];

  for await (const chunk of stream.iterator({ destroyOnReturn: false })) {
    const separator = chunk.indexOf(0x0a);
    if (separator === -1) {
      headerChunks.push(chunk);
      continue;
    }
    headerChunks.push(chunk.subarray(0, separator));
    stream.unshift(chunk.subarray(separator + 1));
    break;
  }

  assert.equal(Buffer.concat(headerChunks).toString(), 'HEAD');
  assert.equal((await buffer(stream)).toString(), 'BODY');
  // 在 end 事件之后再 unshift 属于错误设计；它用于“尚未结束”的解析回退。
});

test('read(0) 不消费数据，但可请求底层 _read 补充缓冲区', async () => {
  let readCalls = 0;
  const stream = new Readable({
    highWaterMark: 4,
    read() {
      readCalls += 1;
      this.push('data');
      this.push(null);
    },
  });

  assert.equal(stream.read(0), null);
  await once(stream, 'readable');
  assert.ok(readCalls >= 1);
  assert.equal(stream.read().toString(), 'data');
  stream.resume();
  await once(stream, 'end');
});

test('Readable.wrap 把旧式 data/end 事件源接入现代 Readable API', async () => {
  class LegacySource extends EventEmitter {
    pause() {
      this.paused = true;
    }

    resume() {
      this.paused = false;
    }
  }

  const legacy = new LegacySource();
  const wrapped = new Readable({ read() {} }).wrap(legacy);
  assert.equal(wrapped.readableObjectMode, false);

  queueMicrotask(() => {
    legacy.emit('data', Buffer.from('legacy '));
    legacy.emit('data', Buffer.from('source'));
    legacy.emit('end');
  });

  assert.equal(await text(wrapped), 'legacy source');
  // 新代码应直接实现 Readable；wrap 主要用于仍采用旧 data/end 协议的依赖。
});
