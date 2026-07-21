// polyglot-covers:
// - nodejs.core.web-url-pattern-component-patterns-test-exec-and-named-groups
// - nodejs.core.web-url-pattern-base-url-relative-input-and-ignore-case
// - nodejs.core.web-url-pattern-wildcards-component-boundaries-and-invalid-input
// - nodejs.core.web-navigator-runtime-metadata-read-only-properties-and-user-agent
// - nodejs.core.web-navigator-locks-worker-lock-manager-identity-and-shared-mode
// - nodejs.core.web-storage-experimental-flag-string-coercion-order-and-methods
// - nodejs.core.web-local-storage-explicit-file-persistence-and-shared-scope-warning
// - nodejs.core.web-session-storage-process-lifetime
// - nodejs.core.web-compression-stream-gzip-deflate-deflate-raw-and-brotli-round-trip
// - nodejs.core.web-text-encoder-decoder-stream-split-code-point-and-byte-sequence
// - nodejs.core.web-count-and-byte-length-queuing-strategies
// - nodejs.core.web-custom-event-detail-and-dom-exception-identity

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdtemp, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { promisify } from 'node:util';
import { locks as workerLocks } from 'node:worker_threads';

const execFileAsync = promisify(execFile);

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

test('URLPattern 分组件匹配 URL，并从命名组提取结构化参数', () => {
  const pattern = new URLPattern({
    protocol: 'https',
    hostname: ':tenant.example.com',
    pathname: '/books/:bookId',
    search: 'format=:format',
  });
  const input = 'https://docs.example.com/books/node-24?format=html';

  assert.equal(pattern.test(input), true);
  assert.equal(pattern.test('http://docs.example.com/books/node-24?format=html'), false);
  assert.equal(pattern.test('https://docs.example.com/authors/node-24?format=html'), false);

  const result = pattern.exec(input);
  assert.notEqual(result, null);
  assert.equal(result.protocol.input, 'https');
  assert.deepEqual(result.protocol.groups, {});
  assert.equal(result.hostname.groups.tenant, 'docs');
  assert.equal(result.pathname.groups.bookId, 'node-24');
  assert.equal(result.search.groups.format, 'html');
  assert.deepEqual(result.inputs, [input]);
  assert.equal(pattern.protocol, 'https');
  assert.equal(pattern.hostname, ':tenant.example.com');
  assert.equal(pattern.pathname, '/books/:bookId');
  // exec 不只返回捕获值，还保留每个 URL 组件的原始 input；匹配不会
  // 跨组件边界。
});

test('URLPattern 用 baseURL 解释相对模式，并可选择大小写不敏感匹配', () => {
  const relative = new URLPattern('/users/:id', 'https://api.example.com/root/');
  assert.equal(relative.protocol, 'https');
  assert.equal(relative.hostname, 'api.example.com');
  assert.equal(relative.pathname, '/users/:id');
  assert.equal(relative.test('https://api.example.com/users/42'), true);
  assert.equal(relative.test('/users/42', 'https://api.example.com'), true);
  assert.equal(relative.test('/users/42', 'https://other.example.com'), false);

  const insensitive = new URLPattern(
    { hostname: 'API.EXAMPLE.COM', pathname: '/Docs/:page' },
    { ignoreCase: true },
  );
  assert.equal(insensitive.test('https://api.example.com/docs/intro'), true);

  const sensitive = new URLPattern({ pathname: '/Docs/:page' });
  assert.equal(sensitive.test('https://example.com/docs/intro'), false);
  // ignoreCase 是构造选项，不是实例上的可读状态；效果要通过 test/exec
  // 观察。
});

test('URLPattern 通配符只吞当前组件，非法输入返回明确结果', () => {
  const assets = new URLPattern({
    hostname: '*.example.com',
    pathname: '/assets/*',
  });
  const matched = assets.exec('https://cdn.eu.example.com/assets/css/app.css');
  assert.notEqual(matched, null);
  assert.equal(matched.hostname.groups[0], 'cdn.eu');
  assert.equal(matched.pathname.groups[0], 'css/app.css');
  assert.equal(assets.test('https://example.net/assets/app.js'), false);

  assert.throws(() => new URLPattern('/relative-without-base'), TypeError);
  assert.equal(assets.exec('not a valid absolute URL'), null);
  // hostname 的 * 不会越过点号规则之外去改变 pathname；各组件分别
  // 编译和匹配。
});

test('navigator 暴露当前 Node 实例元数据，属性来自只读原型访问器', () => {
  assert.ok(navigator instanceof Navigator);
  assert.equal(Number.isInteger(navigator.hardwareConcurrency), true);
  assert.ok(navigator.hardwareConcurrency >= 1);
  assert.equal(typeof navigator.language, 'string');
  assert.ok(navigator.language.length > 0);
  assert.equal(navigator.languages[0], navigator.language);
  assert.equal(typeof navigator.platform, 'string');
  assert.ok(navigator.platform.length > 0);
  assert.equal(navigator.userAgent, `Node.js/${process.versions.node.split('.')[0]}`);

  for (const property of [
    'hardwareConcurrency',
    'language',
    'languages',
    'platform',
    'userAgent',
  ]) {
    const descriptor = Object.getOwnPropertyDescriptor(Navigator.prototype, property);
    assert.equal(descriptor.set, undefined);
    assert.equal(typeof descriptor.get, 'function');
  }
  // 这些值描述运行时/操作系统，不是浏览器指纹，也不能假设跨容器
  // 保持相同。
});

test('navigator.locks 与 worker_threads.locks 同源，共享锁可并存', async () => {
  assert.equal(navigator.locks, workerLocks);
  const name = `polyglot-navigator-shared-${process.pid}`;
  const firstEntered = deferred();
  const secondEntered = deferred();
  const release = deferred();
  const order = [];

  const first = navigator.locks.request(name, { mode: 'shared' }, async (lock) => {
    order.push(`first:${lock.mode}`);
    firstEntered.resolve();
    await release.promise;
  });
  await firstEntered.promise;
  const second = navigator.locks.request(name, { mode: 'shared' }, async (lock) => {
    order.push(`second:${lock.mode}`);
    secondEntered.resolve();
    await release.promise;
  });
  await secondEntered.promise;

  const exclusive = navigator.locks.request(name, (lock) => {
    order.push(`exclusive:${lock.mode}`);
  });
  const snapshot = await navigator.locks.query();
  assert.equal(snapshot.held.filter((lock) => lock.name === name).length, 2);
  assert.equal(snapshot.pending.filter((lock) => lock.name === name).length, 1);

  release.resolve();
  await Promise.all([first, second, exclusive]);
  assert.deepEqual(order, ['first:shared', 'second:shared', 'exclusive:exclusive']);
  // shared 只与同名 exclusive 互斥；不同名称的锁互不影响。
});

async function runWebStorage(file, source) {
  return execFileAsync(process.execPath, [
    '--experimental-webstorage',
    `--localstorage-file=${file}`,
    '--input-type=module',
    '--eval',
    source,
  ], { encoding: 'utf8' });
}

test('Web Storage 字符串化数据，localStorage 文件跨进程持久化', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-webstorage-'));
  const file = join(directory, 'local-storage.db');
  try {
    const first = await runWebStorage(file, `
      localStorage.clear();
      sessionStorage.clear();
      localStorage.setItem('count', 42);
      localStorage.setItem('enabled', true);
      localStorage.setItem('remove-me', 'temporary');
      localStorage.removeItem('remove-me');
      sessionStorage.setItem('transient', 'only-this-process');
      process.stdout.write(JSON.stringify({
        localIsStorage: localStorage instanceof Storage,
        sessionIsStorage: sessionStorage instanceof Storage,
        length: localStorage.length,
        keys: [localStorage.key(0), localStorage.key(1), localStorage.key(2)],
        count: localStorage.getItem('count'),
        enabled: localStorage.getItem('enabled'),
        missing: localStorage.getItem('missing'),
        transient: sessionStorage.getItem('transient'),
      }));
    `);
    assert.deepEqual(JSON.parse(first.stdout), {
      localIsStorage: true,
      sessionIsStorage: true,
      length: 2,
      keys: ['count', 'enabled', null],
      count: '42',
      enabled: 'true',
      missing: null,
      transient: 'only-this-process',
    });

    const second = await runWebStorage(file, `
      process.stdout.write(JSON.stringify({
        count: localStorage.getItem('count'),
        enabled: localStorage.getItem('enabled'),
        transient: sessionStorage.getItem('transient'),
      }));
      localStorage.clear();
    `);
    assert.deepEqual(JSON.parse(second.stdout), {
      count: '42',
      enabled: 'true',
      transient: null,
    });
    assert.ok((await stat(file)).size > 0);
    assert.match(first.stderr, /Web Storage is an experimental feature/);
    assert.match(second.stderr, /Web Storage is an experimental feature/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
  // localStorage 文件未加密，且服务端所有请求共享同一份数据，不应直接
  // 存放秘密或按用户隔离的数据；sessionStorage 只活在当前进程，第二个
  // 进程读不到前一份值。
});

async function collectBytes(stream) {
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function collectTextChunks(stream) {
  const reader = stream.getReader();
  let result = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) return result;
    result += value;
  }
}

test('CompressionStream 与 DecompressionStream 支持四种格式的流式往返', async () => {
  const text = 'Node.js Web Compression：'.repeat(32);
  const original = new TextEncoder().encode(text);

  for (const format of ['gzip', 'deflate', 'deflate-raw', 'brotli']) {
    const compressed = await collectBytes(
      new Blob([original]).stream().pipeThrough(new CompressionStream(format)),
    );
    assert.notDeepEqual(compressed, original);
    const restored = await collectBytes(
      new Blob([compressed]).stream().pipeThrough(new DecompressionStream(format)),
    );
    assert.deepEqual(restored, original);
  }

  assert.throws(() => new CompressionStream('zip'), TypeError);
  assert.throws(() => new DecompressionStream('zip'), TypeError);
  // brotli 是 Node 24.7 加入的格式；流类只处理压缩字节，不提供归档
  // 文件目录语义。
});

test('TextEncoderStream 和 TextDecoderStream 会跨 chunk 保留未完成字符', async () => {
  const encoder = new TextEncoderStream();
  const encodedPromise = collectBytes(encoder.readable);
  const encodingWriter = encoder.writable.getWriter();
  await encodingWriter.write('A\ud83d');
  await encodingWriter.write('\ude00中');
  await encodingWriter.close();
  const encoded = await encodedPromise;
  assert.deepEqual(encoded, new TextEncoder().encode('A😀中'));

  const splitBytes = new TextEncoder().encode('B😀文');
  const decoder = new TextDecoderStream();
  const decodedPromise = collectTextChunks(decoder.readable);
  const decodingWriter = decoder.writable.getWriter();
  await decodingWriter.write(splitBytes.subarray(0, 3));
  await decodingWriter.write(splitBytes.subarray(3));
  await decodingWriter.close();
  assert.equal(await decodedPromise, 'B😀文');
  // 普通 TextEncoder.encode 会把孤立代理项替换为 U+FFFD；流式编码器会
  // 等下一块，让跨 chunk 的代理项对仍组成同一个码点。解码器对拆开的
  // UTF-8 序列也同理。
});

test('Web Streams 队列策略分别按块数和 byteLength 计算背压大小', () => {
  const count = new CountQueuingStrategy({ highWaterMark: 3 });
  assert.equal(count.highWaterMark, 3);
  assert.equal(count.size('any chunk'), 1);
  assert.equal(count.size(new Uint8Array(100)), 1);

  const bytes = new ByteLengthQueuingStrategy({ highWaterMark: 1024 });
  assert.equal(bytes.highWaterMark, 1024);
  assert.equal(bytes.size(new Uint8Array(12)), 12);
  assert.equal(bytes.size({ byteLength: 7 }), 7);
  assert.equal(bytes.size({}), undefined);
  assert.throws(() => new ReadableStream({
    start(controller) {
      controller.enqueue({});
    },
  }, bytes), RangeError);
  // size() 本身只是读取 byteLength；真正入队时，流控制器才校验结果
  // 必须是有限非负数。
});

test('CustomEvent 的 detail 保留原引用，DOMException 同时携带 name 与 message', () => {
  const detail = { lesson: 'events' };
  const event = new CustomEvent('ready', {
    bubbles: true,
    cancelable: true,
    detail,
  });
  assert.ok(event instanceof Event);
  assert.equal(event.detail, detail);
  assert.equal(event.bubbles, true);
  assert.equal(event.cancelable, true);

  const exception = new DOMException('operation stopped', 'AbortError');
  assert.ok(exception instanceof Error);
  assert.equal(exception.name, 'AbortError');
  assert.equal(exception.message, 'operation stopped');
  assert.equal(exception.code, DOMException.ABORT_ERR);
  assert.match(exception.toString(), /^AbortError: operation stopped$/);
  // DOMException 的 code 只为旧名称保留；现代逻辑应检查 name，或直接
  // 传播 signal.reason。
});
