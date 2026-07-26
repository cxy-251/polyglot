// 文件、目录、元数据与链接。
// 共同问题：如何创建和读取文件；目录遍历返回什么；元数据描述链接还是目标；
// 硬链接与符号链接共享哪些身份。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: file_directory_metadata_and_links
// polyglot-related: languages/nodejs/node_core/03_files_paths_and_urls/
// polyglot-related+: test_045_directories_metadata_links_copy_glob_and_removal.mjs

import assert from 'node:assert/strict';
import { mkdtemp, link, lstat, readdir, readFile, rm, stat, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

async function temporaryDirectory(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'polyglot-concept-files-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  return directory;
}

test('文件写入、读取与元数据是显式异步操作', async (t) => {
  const directory = await temporaryDirectory(t);
  const file = path.join(directory, 'note.txt');
  await writeFile(file, '你好', 'utf8');

  assert.equal(await readFile(file, 'utf8'), '你好');
  assert.equal((await stat(file)).size, Buffer.byteLength('你好'));
});

test('目录项可以携带无需额外 stat 的类型提示', async (t) => {
  const directory = await temporaryDirectory(t);
  await writeFile(path.join(directory, 'note.txt'), 'value');

  const entries = await readdir(directory, { withFileTypes: true });

  assert.equal(entries.length, 1);
  assert.equal(entries[0].isFile(), true);
});

test('硬链接名称共享文件内容与身份', async (t) => {
  const directory = await temporaryDirectory(t);
  const original = path.join(directory, 'original.txt');
  const alias = path.join(directory, 'alias.txt');
  await writeFile(original, 'value');
  await link(original, alias);

  assert.equal((await stat(original)).ino, (await stat(alias)).ino);
  assert.equal(await readFile(alias, 'utf8'), 'value');
});

test('lstat 观察符号链接而 stat 跟随目标', async (t) => {
  const directory = await temporaryDirectory(t);
  const target = path.join(directory, 'target.txt');
  const alias = path.join(directory, 'alias.txt');
  await writeFile(target, 'value');
  await symlink(target, alias);

  assert.equal((await lstat(alias)).isSymbolicLink(), true);
  assert.equal((await stat(alias)).isFile(), true);
});
