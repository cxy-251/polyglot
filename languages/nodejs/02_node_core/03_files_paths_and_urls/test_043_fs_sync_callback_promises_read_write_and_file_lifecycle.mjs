// polyglot-covers:
// - nodejs.core.fs-sync-callback-and-promises-api-styles
// - nodejs.core.fs-read-file-buffer-and-encoding
// - nodejs.core.fs-write-file-append-file-and-flags
// - nodejs.core.fs-file-url-paths
// - nodejs.core.fs-access-and-open-race-pitfall
// - nodejs.core.fs-copy-rename-unlink-and-truncate
// - nodejs.core.fs-abort-signal
// - nodejs.core.fs-error-codes

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  constants,
  readFile as readFileCallback,
  readFileSync,
  writeFileSync,
} from 'node:fs';
import {
  access,
  appendFile,
  copyFile,
  mkdtemp,
  open,
  readFile,
  rename,
  rm,
  truncate,
  unlink,
  writeFile,
} from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const createWorkspace = async (t) => {
  const root = await mkdtemp('/tmp/polyglot-nodejs-fs-');
  t.after(() => rm(root, { force: true, recursive: true }));
  return root;
};

test('readFile 不指定 encoding 返回 Buffer，指定后返回字符串', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'text.txt');
  await writeFile(file, 'A中💡', 'utf8');

  const bytes = await readFile(file);
  const text = await readFile(file, 'utf8');

  assert.equal(Buffer.isBuffer(bytes), true);
  assert.equal(bytes.toString('hex'), '41e4b8adf09f92a1');
  assert.equal(text, 'A中💡');
  assert.equal(typeof text, 'string');
});

test('writeFile 接受字符串和字节视图，并默认替换既有文件', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'value.bin');

  await writeFile(file, 'first');
  await writeFile(file, Uint8Array.of(1, 2, 3));
  assert.deepEqual([...await readFile(file)], [1, 2, 3]);

  const source = new Uint8Array([4, 5, 6]);
  await writeFile(file, new DataView(source.buffer, 1, 2));
  assert.deepEqual([...await readFile(file)], [5, 6]);
});

test('flag wx 原子要求新文件，appendFile 总在末尾追加', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'log.txt');

  await writeFile(file, 'first\n', { flag: 'wx' });
  await assert.rejects(
    writeFile(file, 'replacement', { flag: 'wx' }),
    (error) => error.code === 'EEXIST',
  );

  await appendFile(file, 'second\n');
  await appendFile(file, Buffer.from('third\n'));
  assert.equal(await readFile(file, 'utf8'), 'first\nsecond\nthird\n');

  // 先 access 再 write 存在 TOCTOU 竞争；独占创建应直接使用 wx 并处理 EEXIST。
});

test('大多数 fs API 直接接受 file URL，路径中的特殊字符不会误解析', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'value #100%.txt');
  const url = pathToFileURL(file);

  await writeFile(url, 'payload');
  assert.equal(await readFile(url, 'utf8'), 'payload');
  assert.equal(readFileSync(url, 'utf8'), 'payload');
  await unlink(url);
  await assert.rejects(readFile(url), (error) => error.code === 'ENOENT');
});

test('callback API 异步完成，Promise API 更适合组合控制流', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'callback.txt');
  await writeFile(file, 'value');
  const events = [];

  const completed = new Promise((resolve, reject) => {
    readFileCallback(file, 'utf8', (error, value) => {
      if (error) {
        reject(error);
        return;
      }
      events.push(`callback:${value}`);
      resolve();
    });
  });
  events.push('after call');

  assert.deepEqual(events, ['after call']);
  await completed;
  assert.deepEqual(events, ['after call', 'callback:value']);
});

test('同步 API 在返回前完成，适合启动配置而非请求热路径', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'sync.txt');
  const events = [];

  writeFileSync(file, 'sync value');
  events.push('after write');
  const value = readFileSync(file, 'utf8');
  events.push('after read');

  assert.equal(value, 'sync value');
  assert.deepEqual(events, ['after write', 'after read']);
  // 同步文件调用阻塞事件循环；CLI 启动阶段可接受，服务器并发路径通常使用异步 API。
});

test('access 检查当前权限但不能保证下一步仍可访问', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'accessible.txt');
  await writeFile(file, 'value');

  assert.equal(await access(file, constants.F_OK), undefined);
  assert.equal(await access(file, constants.R_OK | constants.W_OK), undefined);
  await assert.rejects(
    access(join(root, 'missing.txt'), constants.F_OK),
    (error) => error.code === 'ENOENT',
  );

  // access 只适合权限提示；真实操作仍必须自己捕获 EACCES/ENOENT 等错误。
});

test('copyFile、rename、truncate 和 unlink 组成常见文件生命周期', async (t) => {
  const root = await createWorkspace(t);
  const source = join(root, 'source.txt');
  const copy = join(root, 'copy.txt');
  const moved = join(root, 'moved.txt');
  await writeFile(source, '0123456789');

  await copyFile(source, copy, constants.COPYFILE_EXCL);
  assert.equal(await readFile(copy, 'utf8'), '0123456789');
  await assert.rejects(
    copyFile(source, copy, constants.COPYFILE_EXCL),
    (error) => error.code === 'EEXIST',
  );

  await rename(copy, moved);
  await truncate(moved, 4);
  assert.equal(await readFile(moved, 'utf8'), '0123');
  await truncate(moved, 6);
  assert.deepEqual([...await readFile(moved)], [48, 49, 50, 51, 0, 0]);

  await unlink(moved);
  await assert.rejects(readFile(moved), (error) => error.code === 'ENOENT');
});

test('已取消 signal 让 readFile/writeFile 以 AbortError 拒绝', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'abort.txt');
  await writeFile(file, 'existing');
  const signal = AbortSignal.abort(new Error('stop'));

  await assert.rejects(
    readFile(file, { signal }),
    (error) => error.name === 'AbortError' && error.cause === signal.reason,
  );
  await assert.rejects(
    writeFile(file, 'new value', { signal }),
    (error) => error.name === 'AbortError' && error.cause === signal.reason,
  );
  assert.equal(await readFile(file, 'utf8'), 'existing');

  // 中途 abort 是“尽力而为”，不能保证磁盘完全没有部分写入；原子替换需临时文件+rename。
});

test('错误对象同时提供稳定 code 和环境相关 syscall/path 信息', async (t) => {
  const root = await createWorkspace(t);
  const missing = join(root, 'missing.txt');

  await assert.rejects(readFile(missing), (error) => {
    assert.equal(error.code, 'ENOENT');
    assert.equal(error.syscall, 'open');
    assert.equal(error.path, missing);
    assert.equal(typeof error.errno, 'number');
    assert.equal(error instanceof Error, true);
    return true;
  });

  const directoryHandle = await open(root, 'r');
  await directoryHandle.close();
});
