// polyglot-covers:
// - nodejs.core.stream-readable-custom-read-and-push
// - nodejs.core.stream-readable-paused-flowing-and-readable-event
// - nodejs.core.stream-readable-encoding-and-multibyte-boundaries
// - nodejs.core.stream-readable-from-and-object-mode
// - nodejs.core.stream-readable-async-iterator-destroy-on-return
// - nodejs.core.stream-readable-iterator-preserve-on-return
// - nodejs.core.stream-readable-map-filter-flat-map-and-reduce

import assert from 'node:assert/strict';
import test from 'node:test';

import { Readable } from 'node:stream';
import { once } from 'node:events';

class SequenceReadable extends Readable {
  constructor(chunks, options = {}) {
    super(options);
    this.chunks = [...chunks];
    this.readRequests = [];
  }

  _read(size) {
    this.readRequests.push(size);
    const chunk = this.chunks.shift();
    this.push(chunk ?? null);
  }
}

test('自定义 Readable 在 _read 中 push 数据，以 push(null) 表示 EOF', async () => {
  const stream = new SequenceReadable([
    Buffer.from('first'),
    Buffer.from('second'),
  ], { highWaterMark: 4 });
  const chunks = [];

  for await (const chunk of stream) {
    chunks.push(chunk);
  }

  assert.equal(Buffer.concat(chunks).toString(), 'firstsecond');
  assert.ok(stream.readRequests.length >= 2);
  assert.ok(stream.readRequests.every((size) => size === 4));
  assert.equal(stream.readableEnded, true);
  assert.equal(stream.destroyed, true);
});

test('readable 事件不进入 flowing 模式，read(size) 主动拉取缓冲数据', async () => {
  const stream = new Readable({
    read() {},
  });
  stream.push('abcdef');
  stream.push(null);

  await once(stream, 'readable');
  // readableFlowing 的三态不能简化成布尔值：null 表示还没有 flowing 消费机制，
  // false 才表示曾经 flowing、后来因 pause/unpipe/背压而暂停。
  assert.equal(stream.readableFlowing, null);
  assert.equal(stream.read(2).toString(), 'ab');
  assert.equal(stream.read(3).toString(), 'cde');
  assert.equal(stream.read().toString(), 'f');
  await once(stream, 'end');
});

test('data listener 切换到 flowing 模式，pause/resume 控制继续分发', async () => {
  const stream = Readable.from(['a', 'b', 'c']);
  const chunks = [];
  let pausedOnce = false;

  stream.on('data', (chunk) => {
    chunks.push(chunk);
    if (!pausedOnce) {
      pausedOnce = true;
      stream.pause();
      queueMicrotask(() => stream.resume());
    }
  });
  await once(stream, 'end');

  assert.deepEqual(chunks, ['a', 'b', 'c']);
  assert.equal(stream.readableFlowing, true);
});

test('setEncoding 跨 Buffer 边界拼接多字节字符并输出字符串', async () => {
  const bytes = Buffer.from('A中💡B');
  const stream = Readable.from([
    bytes.subarray(0, 2),
    bytes.subarray(2, 6),
    bytes.subarray(6),
  ]);
  stream.setEncoding('utf8');
  const chunks = [];

  for await (const chunk of stream) {
    assert.equal(typeof chunk, 'string');
    chunks.push(chunk);
  }
  assert.equal(chunks.join(''), 'A中💡B');
  assert.equal(chunks.includes('�'), false);
});

test('Readable.from 默认 objectMode，保留 iterable 元素身份', async () => {
  const first = { id: 1 };
  const second = { id: 2 };
  const stream = Readable.from([first, second]);

  assert.equal(stream.readableObjectMode, true);
  assert.equal(stream.readableHighWaterMark, 1);
  assert.deepEqual(await stream.toArray(), [first, second]);

  const text = Readable.from('text');
  assert.deepEqual(await text.toArray(), ['text']);
});

test('默认 async iterator 提前退出会 destroy Readable', async () => {
  const stream = Readable.from([1, 2, 3]);
  const observed = [];

  for await (const value of stream) {
    observed.push(value);
    break;
  }

  assert.deepEqual(observed, [1]);
  assert.equal(stream.destroyed, true);
  assert.equal(stream.readableAborted, true);
});

test('iterator destroyOnReturn false 允许提前退出后继续消费', async () => {
  const stream = Readable.from([1, 2, 3]);
  const firstPass = [];

  for await (const value of stream.iterator({ destroyOnReturn: false })) {
    firstPass.push(value);
    break;
  }

  assert.deepEqual(firstPass, [1]);
  assert.equal(stream.destroyed, false);
  assert.deepEqual(await stream.toArray(), [2, 3]);
  assert.equal(stream.destroyed, true);
});

test('map/filter/flatMap 惰性转换 async iterable 并保持输出顺序', async () => {
  const mapped = Readable.from([1, 2, 3, 4])
    .map(async (value) => value * 2, { concurrency: 2 })
    .filter((value) => value > 4)
    .flatMap((value) => [value, -value]);

  assert.deepEqual(await mapped.toArray(), [6, -6, 8, -8]);
});

test('some/every/find 会短路，reduce 按顺序归约全部元素', async () => {
  const someSource = Readable.from([1, 2, 3]);
  let someCalls = 0;
  assert.equal(await someSource.some((value) => {
    someCalls += 1;
    return value === 2;
  }), true);
  assert.equal(someCalls, 2);

  // 函数式消费方法返回结果，并不承诺此时源流的 destroyed 属性已经变为 true；
  // 不应把实现内部的清理调度误当成公开契约。
  someSource.destroy();

  assert.equal(await Readable.from([1, 2, 3]).every((value) => value > 0), true);
  assert.equal(await Readable.from([1, 2, 3]).find((value) => value > 1), 2);
  assert.equal(
    await Readable.from([1, 2, 3]).reduce((total, value) => total + value, 10),
    16,
  );
});

test('map 接受 AbortSignal，并以 AbortError 终止映射流', async () => {
  const controller = new AbortController();
  const stream = Readable.from([1, 2, 3]).map((value) => {
    if (value === 2) {
      controller.abort(new Error('stop mapping'));
    }
    return value;
  }, { signal: controller.signal });

  await assert.rejects(
    stream.toArray(),
    (error) => error.name === 'AbortError' && error.code === 'ABORT_ERR',
  );
  // signal.reason 保留调用者的原因，但流生成的 AbortError 不保证把它复制到 cause。
  assert.equal(controller.signal.reason.message, 'stop mapping');
});
