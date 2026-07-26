// polyglot-covers:
// - nodejs.core.fs-create-read-stream-ranges-and-high-water-mark
// - nodejs.core.fs-create-write-stream-flags-and-finish
// - nodejs.core.fs-stream-file-handle-and-auto-close
// - nodejs.core.fs-stream-pipeline-and-abort
// - nodejs.core.fs-watch-callback-and-async-iterator
// - nodejs.core.fs-watch-abort-signal
// - nodejs.core.fs-open-as-blob

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createReadStream,
  createWriteStream,
  openAsBlob,
  watch as watchCallback,
} from 'node:fs';
import {
  mkdtemp,
  open,
  readFile,
  rm,
  watch,
  writeFile,
} from 'node:fs/promises';
import { join } from 'node:path';
import { Readable, Writable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

const createWorkspace = async (t) => {
  const root = await mkdtemp('/tmp/polyglot-nodejs-fs-streams-');
  t.after(() => rm(root, { force: true, recursive: true }));
  return root;
};

const finished = (stream, event = 'finish') => new Promise((resolve, reject) => {
  stream.once(event, resolve);
  stream.once('error', reject);
});

test('createReadStream 的 start/end 都是包含端点，highWaterMark 控制 chunk 上限', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'range.txt');
  await writeFile(file, '0123456789');
  const stream = createReadStream(file, {
    end: 7,
    highWaterMark: 2,
    start: 2,
  });
  const chunks = [];

  for await (const chunk of stream) {
    chunks.push(chunk);
  }

  assert.equal(Buffer.concat(chunks).toString(), '234567');
  assert.deepEqual(chunks.map(({ length }) => length), [2, 2, 2]);
  assert.equal(stream.closed, true);
});

test('encoding 让 ReadStream 产出字符串并跨 chunk 保持字符完整', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'unicode.txt');
  await writeFile(file, 'A中💡B');
  const stream = createReadStream(file, {
    encoding: 'utf8',
    highWaterMark: 2,
  });
  const chunks = [];

  for await (const chunk of stream) {
    chunks.push(chunk);
    assert.equal(typeof chunk, 'string');
  }

  assert.equal(chunks.join(''), 'A中💡B');
  assert.equal(chunks.includes('�'), false);
});

test('createWriteStream 在 finish 前完成写入，flags 控制覆盖或追加', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'output.txt');
  const first = createWriteStream(file, { flags: 'w' });

  first.write('first');
  first.end('-value');
  await finished(first);
  assert.equal(await readFile(file, 'utf8'), 'first-value');

  const appended = createWriteStream(file, { flags: 'a' });
  appended.end('-appended');
  await finished(appended);
  assert.equal(await readFile(file, 'utf8'), 'first-value-appended');
});

test('FileHandle 创建流时 autoClose false 允许流结束后继续复用句柄', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'handle-stream.txt');
  await writeFile(file, 'payload');
  const handle = await open(file, 'r');

  try {
    const stream = handle.createReadStream({ autoClose: false });
    const chunks = [];
    for await (const chunk of stream) {
      chunks.push(chunk);
    }
    assert.equal(Buffer.concat(chunks).toString(), 'payload');
    assert.equal((await handle.stat()).size, 7);
  } finally {
    await handle.close();
  }
});

test('pipeline 连接文件流与 Transform/Writable 并统一传播完成', async (t) => {
  const root = await createWorkspace(t);
  const source = join(root, 'source.txt');
  const destination = join(root, 'destination.txt');
  await writeFile(source, 'polyglot node');

  async function* uppercase(chunks) {
    for await (const chunk of chunks) {
      yield chunk.toString().toUpperCase();
    }
  }

  await pipeline(
    createReadStream(source),
    uppercase,
    createWriteStream(destination),
  );
  assert.equal(await readFile(destination, 'utf8'), 'POLYGLOT NODE');
});

test('pipeline 接收已取消 signal 并销毁参与流', async () => {
  const source = Readable.from(['one', 'two']);
  const destination = new Writable({
    write(chunk, encoding, callback) {
      callback();
    },
  });
  const signal = AbortSignal.abort(new Error('cancel pipeline'));

  await assert.rejects(
    pipeline(source, destination, { signal }),
    (error) => error.name === 'AbortError',
  );
  assert.equal(source.destroyed, true);
  assert.equal(destination.destroyed, true);
});

test('fs.promises.watch 作为 async iterator 产生事件并由 signal 关闭', async (t) => {
  const root = await createWorkspace(t);
  const controller = new AbortController();
  const events = watch(root, { signal: controller.signal });
  const pending = events.next();
  await writeFile(join(root, 'created.txt'), 'value');

  const event = await pending;
  assert.equal(event.done, false);
  assert.ok(['change', 'rename'].includes(event.value.eventType));
  assert.equal(event.value.filename, 'created.txt');

  controller.abort();
  const queuedEvents = [];
  let terminated = false;
  for (let attempt = 0; attempt < 10 && !terminated; attempt += 1) {
    try {
      const next = await events.next();
      if (next.done) {
        terminated = true;
      } else {
        queuedEvents.push(next.value);
      }
    } catch (error) {
      assert.equal(error.name, 'AbortError');
      terminated = true;
    }
  }
  assert.equal(terminated, true);
  assert.ok(queuedEvents.every(({ filename }) => filename === 'created.txt'));

  // watcher 事件可能合并或重复，不能把每次写入与事件数量做一一对应。
});

test('callback fs.watch 返回 FSWatcher，可 close 且支持 abort signal', async (t) => {
  const root = await createWorkspace(t);
  const controller = new AbortController();
  const eventPromise = new Promise((resolve) => {
    const watcher = watchCallback(root, { signal: controller.signal }, (
      eventType,
      filename,
    ) => resolve({ eventType, filename, watcher }));
  });

  await writeFile(join(root, 'callback.txt'), 'value');
  const { eventType, filename, watcher } = await eventPromise;
  assert.ok(['change', 'rename'].includes(eventType));
  assert.equal(filename, 'callback.txt');
  controller.abort();
  assert.equal(watcher.close(), undefined);
});

test('openAsBlob 创建 file-backed Blob，读取时检查文件是否被修改', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'blob.txt');
  await writeFile(file, 'original');

  const blob = await openAsBlob(file, { type: 'text/plain' });
  assert.equal(blob.size, 8);
  assert.equal(blob.type, 'text/plain');
  assert.equal(await blob.text(), 'original');

  const changed = await openAsBlob(file);
  await writeFile(file, 'modified content');
  await assert.rejects(
    changed.text(),
    (error) => error.name === 'NotReadableError',
  );
});
