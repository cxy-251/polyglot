// polyglot-covers:
// - nodejs.core.fs-mkdir-readdir-and-opendir
// - nodejs.core.fs-dirent-and-recursive-traversal
// - nodejs.core.fs-stat-lstat-and-statfs
// - nodejs.core.fs-symbolic-hard-links-readlink-and-realpath
// - nodejs.core.fs-cp-recursive-filter-and-preserve-timestamps
// - nodejs.core.fs-glob-and-exclude
// - nodejs.core.fs-mkdtemp-prefix-pitfall
// - nodejs.core.fs-rm-recursive-force-and-rmdir-boundary

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  cp,
  glob,
  link,
  lstat,
  mkdir,
  mkdtemp,
  opendir,
  readFile,
  readdir,
  readlink,
  realpath,
  rm,
  rmdir,
  stat,
  statfs,
  symlink,
  utimes,
  writeFile,
} from 'node:fs/promises';
import { basename, dirname, join } from 'node:path';

const createWorkspace = async (t) => {
  const root = await mkdtemp('/tmp/polyglot-nodejs-directories-');
  t.after(() => rm(root, { force: true, recursive: true }));
  return root;
};

const buildTree = async (root) => {
  await mkdir(join(root, 'src', 'nested'), { recursive: true });
  await mkdir(join(root, 'empty'));
  await writeFile(join(root, 'README.md'), 'root');
  await writeFile(join(root, 'src', 'index.mjs'), 'export default 1;');
  await writeFile(join(root, 'src', 'ignored.tmp'), 'temporary');
  await writeFile(join(root, 'src', 'nested', 'value.mjs'), 'export default 2;');
};

test('mkdir recursive 创建整条路径并报告首个实际创建目录', async (t) => {
  const root = await createWorkspace(t);
  const nested = join(root, 'a', 'b', 'c');

  const created = await mkdir(nested, { recursive: true });
  assert.equal(created, join(root, 'a'));
  assert.equal((await stat(nested)).isDirectory(), true);

  assert.equal(await mkdir(nested, { recursive: true }), undefined);
  await assert.rejects(mkdir(nested), (error) => error.code === 'EEXIST');
});

test('readdir 默认返回名称，withFileTypes 返回不额外 stat 的 Dirent', async (t) => {
  const root = await createWorkspace(t);
  await buildTree(root);

  assert.deepEqual((await readdir(root)).toSorted(), ['README.md', 'empty', 'src']);
  const entries = await readdir(root, { withFileTypes: true });
  const byName = Object.fromEntries(entries.map((entry) => [entry.name, entry]));

  assert.equal(byName['README.md'].isFile(), true);
  assert.equal(byName.src.isDirectory(), true);
  assert.equal(byName.empty.isDirectory(), true);
  assert.equal(byName.src.parentPath, root);
});

test('recursive readdir 返回后代，Dirent.parentPath 用于恢复完整路径', async (t) => {
  const root = await createWorkspace(t);
  await buildTree(root);

  const entries = await readdir(root, {
    recursive: true,
    withFileTypes: true,
  });
  const relativePaths = entries
    .map((entry) => join(entry.parentPath, entry.name).slice(root.length + 1))
    .toSorted();

  assert.deepEqual(relativePaths, [
    'README.md',
    'empty',
    'src',
    'src/ignored.tmp',
    'src/index.mjs',
    'src/nested',
    'src/nested/value.mjs',
  ]);
});

test('opendir 的 async iterator 按需读取并在循环结束后关闭目录', async (t) => {
  const root = await createWorkspace(t);
  await buildTree(root);
  const directory = await opendir(root, { bufferSize: 2 });
  const names = [];

  for await (const entry of directory) {
    names.push(entry.name);
  }
  assert.deepEqual(names.toSorted(), ['README.md', 'empty', 'src']);
  await assert.rejects(
    directory.read(),
    (error) => error.code === 'ERR_DIR_CLOSED',
  );
});

test('stat 跟随符号链接，lstat 描述链接自身', async (t) => {
  const root = await createWorkspace(t);
  const target = join(root, 'target.txt');
  const symbolic = join(root, 'symbolic.txt');
  await writeFile(target, 'payload');
  await symlink('target.txt', symbolic);

  const followed = await stat(symbolic);
  const linkMetadata = await lstat(symbolic);

  assert.equal(followed.isFile(), true);
  assert.equal(followed.isSymbolicLink(), false);
  assert.equal(linkMetadata.isSymbolicLink(), true);
  assert.equal(await readlink(symbolic), 'target.txt');
  assert.equal(await realpath(symbolic), target);
  assert.equal(await readFile(symbolic, 'utf8'), 'payload');
});

test('硬链接共享 inode 和内容，删除一个名字不删除剩余链接', async (t) => {
  const root = await createWorkspace(t);
  const first = join(root, 'first.txt');
  const second = join(root, 'second.txt');
  await writeFile(first, 'shared');
  await link(first, second);

  const firstMetadata = await stat(first);
  const secondMetadata = await stat(second);
  assert.equal(firstMetadata.ino, secondMetadata.ino);
  assert.ok(firstMetadata.nlink >= 2);

  await writeFile(second, 'updated');
  assert.equal(await readFile(first, 'utf8'), 'updated');
  await rm(first);
  assert.equal(await readFile(second, 'utf8'), 'updated');
});

test('stat 支持 bigint，birthtime 等字段受文件系统能力约束', async (t) => {
  const root = await createWorkspace(t);
  const file = join(root, 'metadata.txt');
  await writeFile(file, '12345');

  const ordinary = await stat(file);
  const big = await stat(file, { bigint: true });
  assert.equal(ordinary.size, 5);
  assert.equal(big.size, 5n);
  assert.equal(typeof ordinary.mode, 'number');
  assert.equal(typeof big.mode, 'bigint');
  assert.equal(ordinary.mtime instanceof Date, true);
  assert.equal(Number.isFinite(ordinary.birthtimeMs), true);
});

test('statfs 描述承载路径的文件系统容量而不是单个文件', async (t) => {
  const root = await createWorkspace(t);
  const ordinary = await statfs(root);
  const big = await statfs(root, { bigint: true });

  assert.equal(typeof ordinary.bsize, 'number');
  assert.equal(typeof ordinary.blocks, 'number');
  assert.equal(typeof big.bsize, 'bigint');
  assert.equal(typeof big.blocks, 'bigint');
  assert.ok(ordinary.bsize > 0);
  assert.ok(ordinary.blocks >= ordinary.bfree);
});

test('cp recursive 复制目录树，filter 可跳过路径', async (t) => {
  const root = await createWorkspace(t);
  const source = join(root, 'source');
  const destination = join(root, 'destination');
  await buildTree(source);

  await cp(source, destination, {
    filter: (path) => !path.endsWith('.tmp'),
    recursive: true,
  });

  assert.equal(await readFile(join(destination, 'README.md'), 'utf8'), 'root');
  assert.equal(
    await readFile(join(destination, 'src', 'nested', 'value.mjs'), 'utf8'),
    'export default 2;',
  );
  await assert.rejects(
    stat(join(destination, 'src', 'ignored.tmp')),
    (error) => error.code === 'ENOENT',
  );
});

test('cp preserveTimestamps 保留文件 mtime，force/errorOnExist 控制冲突', async (t) => {
  const root = await createWorkspace(t);
  const source = join(root, 'source.txt');
  const destination = join(root, 'destination.txt');
  const timestamp = new Date('2026-01-02T03:04:05.000Z');
  await writeFile(source, 'source');
  await utimes(source, timestamp, timestamp);

  await cp(source, destination, { preserveTimestamps: true });
  assert.equal((await stat(destination)).mtimeMs, timestamp.getTime());

  await assert.rejects(
    cp(source, destination, { errorOnExist: true, force: false }),
    (error) => error.code === 'ERR_FS_CP_EEXIST',
  );
});

test('glob 返回 async iterator，并可按模式排除结果', async (t) => {
  const root = await createWorkspace(t);
  await buildTree(root);

  const modules = await Array.fromAsync(glob('**/*.mjs', { cwd: root }));
  assert.deepEqual(modules.toSorted(), ['src/index.mjs', 'src/nested/value.mjs']);

  const withoutNested = await Array.fromAsync(glob('**/*', {
    cwd: root,
    exclude: ['**/nested', '**/nested/**'],
  }));
  assert.ok(withoutNested.includes('README.md'));
  assert.equal(withoutNested.some((name) => name.includes('nested')), false);
});

test('mkdtemp 把随机字符直接附加到 prefix，父目录需显式带分隔符', async (t) => {
  const root = await createWorkspace(t);
  const parent = join(root, 'temporary');
  await mkdir(parent);

  const desiredInside = await mkdtemp(join(parent, 'entry-'));
  assert.equal(dirname(desiredInside), parent);
  assert.equal(basename(desiredInside).startsWith('entry-'), true);

  const appendedToName = await mkdtemp(parent);
  assert.equal(dirname(appendedToName), root);
  assert.equal(basename(appendedToName).startsWith('temporary'), true);
  await rm(appendedToName, { recursive: true });
});

test('rm recursive 删除目录树，force 只忽略不存在而非所有错误', async (t) => {
  const root = await createWorkspace(t);
  const tree = join(root, 'tree');
  await buildTree(tree);

  await assert.rejects(rmdir(tree), (error) => error.code === 'ENOTEMPTY');
  await rm(tree, { recursive: true });
  await assert.rejects(stat(tree), (error) => error.code === 'ENOENT');
  assert.equal(await rm(tree, { force: true, recursive: true }), undefined);

  // 新代码删除非空树使用 rm；rmdir recursive 已弃用，rmdir 保留给空目录。
});
