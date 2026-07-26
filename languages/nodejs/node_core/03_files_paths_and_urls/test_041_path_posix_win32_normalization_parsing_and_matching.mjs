// polyglot-covers:
// - nodejs.core.path-join-resolve-and-normalize
// - nodejs.core.path-relative-and-is-absolute
// - nodejs.core.path-basename-dirname-extname
// - nodejs.core.path-parse-and-format
// - nodejs.core.path-posix-and-win32
// - nodejs.core.path-matches-glob
// - nodejs.core.path-delimiter-separator-and-namespaced-path

import assert from 'node:assert/strict';
import test from 'node:test';

import path, {
  basename,
  delimiter,
  dirname,
  extname,
  format,
  isAbsolute,
  join,
  matchesGlob,
  normalize,
  parse,
  posix,
  relative,
  resolve,
  sep,
  toNamespacedPath,
  win32,
} from 'node:path';

test('join 拼接并规范化片段，resolve 从右向左形成绝对路径', () => {
  assert.equal(join('/srv', 'app', '..', 'data', 'file.txt'), '/srv/data/file.txt');
  assert.equal(join('a', '', 'b'), 'a/b');
  assert.equal(join(), '.');

  assert.equal(resolve('/srv/app', '../data'), '/srv/data');
  assert.equal(resolve('/first', '/second', 'file'), '/second/file');
  assert.equal(isAbsolute(resolve('relative')), true);

  // resolve 的相对结果依赖 process.cwd；测试绝对基准时应显式把基准作为首个参数。
});

test('normalize 折叠分隔符和点段，但不会验证路径是否存在', () => {
  assert.equal(normalize('/srv//app/./data/../file'), '/srv/app/file');
  assert.equal(normalize('a/../../b'), '../b');
  assert.equal(normalize('/../../b'), '/b');
  assert.equal(normalize(''), '.');
  assert.equal(normalize('/definitely/missing/../path'), '/definitely/path');
});

test('relative 计算从一个绝对位置到另一个位置的词法路径', () => {
  assert.equal(relative('/srv/app/src', '/srv/app/test/file.mjs'), '../test/file.mjs');
  assert.equal(relative('/srv/app', '/srv/app'), '');

  const from = '/tmp/polyglot-nodejs/a';
  const to = '/tmp/polyglot-nodejs/a/b/c';
  assert.equal(resolve(from, relative(from, to)), to);
});

test('basename、dirname 与 extname 只按路径文本工作', () => {
  const file = '/srv/archive/report.final.txt';

  assert.equal(basename(file), 'report.final.txt');
  assert.equal(basename(file, '.txt'), 'report.final');
  assert.equal(dirname(file), '/srv/archive');
  assert.equal(extname(file), '.txt');
  assert.equal(extname('/srv/.env'), '');
  assert.equal(extname('/srv/file.'), '.');
  assert.equal(extname('/srv/archive.tar.gz'), '.gz');
});

test('parse 分解路径，format 以 dir/root 和 name/ext/base 优先级重建', () => {
  const parts = parse('/home/user/archive.tar.gz');
  assert.deepEqual(parts, {
    base: 'archive.tar.gz',
    dir: '/home/user',
    ext: '.gz',
    name: 'archive.tar',
    root: '/',
  });
  assert.equal(format(parts), '/home/user/archive.tar.gz');
  assert.equal(format({ dir: '/tmp', name: 'report', ext: '.txt' }), '/tmp/report.txt');

  assert.equal(
    format({ base: 'base.bin', dir: '/tmp', ext: '.txt', name: 'ignored' }),
    '/tmp/base.bin',
  );
});

test('posix/win32 可在任意宿主机按目标平台规则处理路径', () => {
  assert.equal(posix.join('C:\\temp', 'file.txt'), 'C:\\temp/file.txt');
  assert.equal(win32.join('C:\\temp', 'folder', '..', 'file.txt'), 'C:\\temp\\file.txt');
  assert.equal(win32.isAbsolute('C:\\temp\\file.txt'), true);
  assert.equal(win32.isAbsolute('C:file.txt'), false);
  assert.equal(win32.basename('C:\\temp\\file.txt'), 'file.txt');
  assert.equal(win32.dirname('C:\\temp\\file.txt'), 'C:\\temp');

  // 默认 path 跟随运行平台；处理外部 Windows 路径时不能在 POSIX 上直接使用默认方法。
  assert.equal(path, posix);
});

test('win32 识别 UNC、drive-relative 与不同盘符的 relative 结果', () => {
  assert.equal(win32.isAbsolute('\\\\server\\share\\file'), true);
  assert.deepEqual(win32.parse('C:\\dir\\file.txt'), {
    base: 'file.txt',
    dir: 'C:\\dir',
    ext: '.txt',
    name: 'file',
    root: 'C:\\',
  });
  assert.equal(win32.relative('C:\\a', 'C:\\a\\b'), 'b');
  assert.equal(win32.relative('C:\\a', 'D:\\b'), 'D:\\b');

  // C:foo 是相对于 C 盘当前目录，不等同于 C:\\foo；跨盘 relative 会返回绝对目标。
});

test('matchesGlob 匹配路径文本并遵循当前 path 平台规则', () => {
  assert.equal(matchesGlob('src/app.test.mjs', 'src/*.test.mjs'), true);
  assert.equal(matchesGlob('src/nested/app.test.mjs', 'src/*.test.mjs'), false);
  assert.equal(matchesGlob('src/nested/app.test.mjs', 'src/**/*.test.mjs'), true);
  assert.equal(posix.matchesGlob('src/app.js', 'src/*.{js,mjs}'), true);
  assert.equal(win32.matchesGlob('src\\app.js', 'src\\*.js'), true);

  // glob 匹配不是文件发现；它不访问磁盘，也不会说明匹配文件实际存在。
});

test('sep/delimiter 服务路径列表协议，toNamespacedPath 主要供 Windows 使用', () => {
  assert.equal(sep, '/');
  assert.equal(delimiter, ':');
  assert.deepEqual('/bin:/usr/bin'.split(delimiter), ['/bin', '/usr/bin']);
  assert.equal(posix.delimiter, ':');
  assert.equal(win32.delimiter, ';');
  assert.equal(toNamespacedPath('/tmp/file'), '/tmp/file');
  assert.equal(win32.toNamespacedPath('C:\\temp\\file'), '\\\\?\\C:\\temp\\file');
});

test('path 方法要求字符串，不会自动接受 URL 或任意对象', () => {
  assert.throws(() => join('/tmp', 7), (error) => error.code === 'ERR_INVALID_ARG_TYPE');
  assert.throws(
    () => basename(new URL('file:///tmp/file.txt')),
    (error) => error.code === 'ERR_INVALID_ARG_TYPE',
  );

  // fs 多数 API 可直接接受 file URL；path 是纯字符串模块，需要先用 fileURLToPath。
});
