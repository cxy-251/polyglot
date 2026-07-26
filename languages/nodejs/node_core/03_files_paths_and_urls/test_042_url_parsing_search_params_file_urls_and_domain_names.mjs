// polyglot-covers:
// - nodejs.core.url-construction-resolution-and-mutation
// - nodejs.core.url-can-parse-and-parse
// - nodejs.core.url-search-params-duplicates-sort-and-encoding
// - nodejs.core.url-file-url-path-conversion
// - nodejs.core.url-to-http-options
// - nodejs.core.url-domain-to-ascii-and-unicode
// - nodejs.core.url-format-and-legacy-boundary

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  URL,
  URLSearchParams,
  domainToASCII,
  domainToUnicode,
  fileURLToPath,
  format,
  pathToFileURL,
  urlToHttpOptions,
} from 'node:url';

test('URL 需要绝对输入或显式 base，并按标准规则解析相对引用', () => {
  assert.throws(() => new URL('/relative'), TypeError);

  const base = new URL('https://example.test/docs/guide/index.html');
  assert.equal(new URL('../api?version=1#top', base).href, (
    'https://example.test/docs/api?version=1#top'
  ));
  assert.equal(new URL('/root', base).href, 'https://example.test/root');
  assert.equal(new URL('//cdn.example.test/a', base).href, 'https://cdn.example.test/a');
});

test('URL 字段赋值会重新序列化并执行百分号编码', () => {
  const url = new URL('https://user:pass@example.test:8443/path');
  url.pathname = '/中文 file';
  url.searchParams.set('q', 'a b&c');
  url.hash = 'section 1';

  assert.equal(url.protocol, 'https:');
  assert.equal(url.username, 'user');
  assert.equal(url.password, 'pass');
  assert.equal(url.host, 'example.test:8443');
  assert.equal(url.pathname, '/%E4%B8%AD%E6%96%87%20file');
  assert.equal(url.search, '?q=a+b%26c');
  assert.equal(url.hash, '#section%201');

  // href 含凭据时不要直接写入日志；URL 不会替应用自动隐藏 password。
});

test('URL.canParse 返回布尔值，URL.parse 对无效输入返回 null', () => {
  assert.equal(URL.canParse('https://example.test'), true);
  assert.equal(URL.canParse('/path', 'https://example.test'), true);
  assert.equal(URL.canParse('/path'), false);
  assert.equal(URL.parse('not an absolute URL'), null);

  const parsed = URL.parse('/path', 'https://example.test');
  assert.equal(parsed instanceof URL, true);
  assert.equal(parsed.href, 'https://example.test/path');
});

test('searchParams 保留重复键和顺序，get 与 getAll 意图不同', () => {
  const params = new URLSearchParams('tag=one&tag=two&empty=&flag');

  assert.equal(params.get('tag'), 'one');
  assert.deepEqual(params.getAll('tag'), ['one', 'two']);
  assert.equal(params.has('empty'), true);
  assert.equal(params.get('empty'), '');
  assert.equal(params.get('flag'), '');
  assert.equal(params.get('missing'), null);
  assert.deepEqual([...params.keys()], ['tag', 'tag', 'empty', 'flag']);
});

test('append/set/delete/sort 就地修改参数，sort 保持同名值相对顺序', () => {
  const params = new URLSearchParams();
  params.append('z', 'last');
  params.append('a', 'first');
  params.append('a', 'second');
  params.set('m', 'middle');
  params.sort();

  assert.equal(params.toString(), 'a=first&a=second&m=middle&z=last');
  params.set('a', 'replacement');
  assert.deepEqual(params.getAll('a'), ['replacement']);
  params.delete('m');
  assert.equal(params.has('m'), false);
});

test('URLSearchParams 使用 form 编码，空格为 +，字面 + 必须编码', () => {
  const params = new URLSearchParams();
  params.set('query', 'a b+c~d');

  assert.equal(params.toString(), 'query=a+b%2Bc%7Ed');
  assert.equal(new URLSearchParams('query=a+b').get('query'), 'a b');
  assert.equal(new URLSearchParams('query=a%2Bb').get('query'), 'a+b');

  // 不要先手工百分号编码再交给 URLSearchParams，否则 % 会再次编码。
});

test('URL.search 与 searchParams 共享状态，但序列化规则可能改变 href', () => {
  const url = new URL('https://example.test/?a=b%20~');
  assert.equal(url.search, '?a=b%20~');
  assert.equal(url.searchParams.get('a'), 'b ~');

  url.searchParams.sort();
  assert.equal(url.search, '?a=b+%7E');
  assert.equal(url.searchParams.get('a'), 'b ~');
});

test('pathToFileURL 正确编码 #、%、空格，fileURLToPath 正确解码', () => {
  const path = '/tmp/polyglot #100%/文件.txt';
  const url = pathToFileURL(path);

  assert.equal(url.protocol, 'file:');
  assert.equal(
    url.href,
    'file:///tmp/polyglot%20%23100%25/%E6%96%87%E4%BB%B6.txt',
  );
  assert.equal(fileURLToPath(url), path);

  // `new URL(`file://${path}`)` 会把 # 当 fragment、% 当转义起点；必须用专用转换函数。
});

test('fileURLToPath 拒绝非 file URL 并处理 localhost', () => {
  assert.equal(fileURLToPath('file://localhost/tmp/file'), '/tmp/file');
  assert.throws(
    () => fileURLToPath('https://example.test/file'),
    (error) => error.code === 'ERR_INVALID_URL_SCHEME',
  );
  assert.throws(
    () => fileURLToPath('file://server/share'),
    (error) => error.code === 'ERR_INVALID_FILE_URL_HOST',
  );
});

test('urlToHttpOptions 生成 http.request 可接受的字段并保留 Symbol 属性', () => {
  const marker = Symbol('marker');
  const url = new URL('https://user:pass@example.test:8443/a?q=1#ignored');
  url[marker] = 7;

  const options = urlToHttpOptions(url);
  assert.equal(options.protocol, 'https:');
  assert.equal(options.hostname, 'example.test');
  assert.equal(options.port, 8443);
  assert.equal(options.path, '/a?q=1');
  assert.equal(options.auth, 'user:pass');
  assert.equal(options[marker], 7);
  assert.equal(Object.hasOwn(options, 'hash'), true);
});

test('国际化域名在 Unicode 与 ASCII/Punycode 之间转换', () => {
  assert.equal(domainToASCII('例子.测试'), 'xn--fsqu00a.xn--0zwm56d');
  assert.equal(domainToUnicode('xn--fsqu00a.xn--0zwm56d'), '例子.测试');
  assert.equal(new URL('https://例子.测试').hostname, 'xn--fsqu00a.xn--0zwm56d');
  assert.equal(domainToASCII('invalid domain %'), '');
});

test('url.format 可控制认证、fragment、search 和 Unicode host 显示', () => {
  const url = new URL('https://user:pass@xn--fsqu00a.xn--0zwm56d/path?q=1#top');

  assert.equal(format(url, {
    auth: false,
    fragment: false,
    search: false,
    unicode: true,
  }), 'https://例子.测试/path');

  assert.equal(format(url, { auth: false }), (
    'https://xn--fsqu00a.xn--0zwm56d/path?q=1#top'
  ));
});
