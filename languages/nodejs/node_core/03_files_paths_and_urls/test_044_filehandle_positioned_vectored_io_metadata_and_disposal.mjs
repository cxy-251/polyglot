// polyglot-covers:
// - nodejs.core.fs-file-handle-open-close-and-async-dispose
// - nodejs.core.fs-file-handle-read-write-and-position
// - nodejs.core.fs-file-handle-readv-writev
// - nodejs.core.fs-file-handle-truncate-stat-chmod-and-utimes
// - nodejs.core.fs-file-handle-sync-and-datasync
// - nodejs.core.fs-file-handle-read-file-write-file-cursor
// - nodejs.core.fs-file-handle-readable-web-stream

import assert from 'node:assert/strict';
import test from 'node:test';

import { mkdtemp, open, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const createWorkspace = async (t) => {
  const root = await mkdtemp('/tmp/polyglot-nodejs-filehandle-');
  t.after(() => rm(root, { force: true, recursive: true }));
  return root;
};

test('open 返回 FileHandle，显式 close 后操作以 EBADF 失败', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'value.txt');
  const handle = await open(file, 'w+');

  assert.equal(typeof handle.fd, 'number');
  assert.equal(await handle.writeFile('payload'), undefined);
  await handle.close();

  await assert.rejects(
    handle.readFile(),
    (error) => error.code === 'EBADF' || error.code === 'ERR_INVALID_STATE',
  );
  assert.equal(await readFile(file, 'utf8'), 'payload');
});

test('await using 通过 Symbol.asyncDispose 自动关闭 FileHandle', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'using.txt');
  let descriptor;

  {
    await using handle = await open(file, 'w+');
    descriptor = handle.fd;
    await handle.writeFile('managed');
  }

  assert.equal(await readFile(file, 'utf8'), 'managed');
  const probe = await open(file, 'r');
  assert.notEqual(probe.fd, undefined);
  await probe.close();
  assert.equal(typeof descriptor, 'number');
});

test('read/write 的显式 position 不推进隐式文件游标', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'position.bin');
  await writeFile(file, Buffer.from('abcdefghij'));
  const handle = await open(file, 'r+');
  t.after(() => handle.close());

  const first = Buffer.alloc(3);
  const positioned = await handle.read(first, 0, 3, 4);
  assert.equal(positioned.bytesRead, 3);
  assert.equal(first.toString(), 'efg');

  const fromCursor = Buffer.alloc(3);
  await handle.read(fromCursor, 0, 3, null);
  assert.equal(fromCursor.toString(), 'abc');

  await handle.write(Buffer.from('XY'), 0, 2, 5);
  await handle.write(Buffer.from('12'), 0, 2, null);
  assert.equal(await readFile(file, 'utf8'), 'abc12XYhij');
});

test('read 可自动分配 Buffer，offset/length 形式适合复用缓冲区', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'read.bin');
  await writeFile(file, '0123456789');
  const handle = await open(file, 'r');
  t.after(() => handle.close());

  const allocated = await handle.read({ length: 4, position: 2 });
  assert.equal(allocated.bytesRead, 4);
  assert.ok(allocated.buffer.length >= allocated.bytesRead);
  assert.equal(
    allocated.buffer.subarray(0, allocated.bytesRead).toString(),
    '2345',
  );

  // 自动 Buffer 的容量可能大于本次数据量，只有 [0, bytesRead) 是有效读取结果。

  const reusable = Buffer.alloc(8, 0x2e);
  const result = await handle.read(reusable, 2, 3, 6);
  assert.equal(result.buffer, reusable);
  assert.deepEqual([...reusable], [46, 46, 54, 55, 56, 46, 46, 46]);
});

test('readv/writev 用多个 Buffer 完成一次 vectored I/O', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'vectors.bin');
  const handle = await open(file, 'w+');
  t.after(() => handle.close());

  const written = await handle.writev([
    Buffer.from('header:'),
    Buffer.from('payload'),
  ], 0);
  assert.equal(written.bytesWritten, 14);

  const header = Buffer.alloc(7);
  const payload = Buffer.alloc(7);
  const read = await handle.readv([header, payload], 0);
  assert.equal(read.bytesRead, 14);
  assert.equal(header.toString(), 'header:');
  assert.equal(payload.toString(), 'payload');
});

test('truncate 改变长度，stat 暴露 BigInt 或 Number 元数据', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'metadata.bin');
  const handle = await open(file, 'w+');
  t.after(() => handle.close());
  await handle.writeFile('123456');

  await handle.truncate(3);
  const ordinary = await handle.stat();
  const big = await handle.stat({ bigint: true });

  assert.equal(ordinary.size, 3);
  assert.equal(big.size, 3n);
  assert.equal(ordinary.isFile(), true);
  assert.equal(ordinary.isDirectory(), false);

  await handle.truncate(5);
  assert.deepEqual([...await readFile(file)], [49, 50, 51, 0, 0]);
});

test('chmod 与 utimes 更新权限位和时间戳', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'attributes.txt');
  const handle = await open(file, 'w+');
  t.after(() => handle.close());
  await handle.writeFile('value');

  await handle.chmod(0o640);
  const timestamp = new Date('2026-07-22T00:00:00.000Z');
  await handle.utimes(timestamp, timestamp);
  const metadata = await stat(file);

  assert.equal(metadata.mode & 0o777, 0o640);
  assert.equal(metadata.atimeMs, timestamp.getTime());
  assert.equal(metadata.mtimeMs, timestamp.getTime());
});

test('datasync/sync 在成功时返回 undefined，但持久性保证由文件系统决定', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'durable.txt');
  const handle = await open(file, 'w');
  t.after(() => handle.close());

  await handle.writeFile('value');
  assert.equal(await handle.datasync(), undefined);
  assert.equal(await handle.sync(), undefined);

  // datasync 侧重文件数据，sync 还要求相关元数据；硬件缓存和目录项另有平台语义。
});

test('writeFile/readFile 使用当前游标，重复调用不会自动回到开头', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'cursor.txt');
  const handle = await open(file, 'w+');
  t.after(() => handle.close());

  await handle.writeFile('first');
  await handle.writeFile('second');
  assert.equal(await readFile(file, 'utf8'), 'firstsecond');

  // 当前游标已经在末尾，因此同一 handle.readFile 只读到剩余的空内容。
  assert.equal((await handle.readFile('utf8')), '');
  const positioned = Buffer.alloc(5);
  await handle.read(positioned, 0, 5, 0);
  assert.equal(positioned.toString(), 'first');
});

test('readableWebStream 把 FileHandle 暴露为一次性 Web ReadableStream', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'web-stream.txt');
  await writeFile(file, 'stream payload');
  const handle = await open(file, 'r');

  const stream = handle.readableWebStream({ type: 'bytes' });
  const response = new Response(stream);
  assert.equal(await response.text(), 'stream payload');

  assert.throws(
    () => handle.readableWebStream(),
    (error) => error.code === 'ERR_INVALID_STATE',
  );
  await handle.close();
});
