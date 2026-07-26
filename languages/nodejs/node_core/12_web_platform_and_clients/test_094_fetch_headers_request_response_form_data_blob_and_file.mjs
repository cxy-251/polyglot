// polyglot-covers:
// - nodejs.core.web-headers-normalization-append-set-delete-iteration-and-set-cookie
// - nodejs.core.web-blob-bytes-text-array-buffer-slice-and-stream
// - nodejs.core.web-file-name-type-last-modified-and-blob-inheritance
// - nodejs.core.web-form-data-multiple-values-set-delete-file-and-multipart-encoding
// - nodejs.core.web-request-clone-body-used-method-body-and-duplex-stream-requirement
// - nodejs.core.web-response-json-error-redirect-clone-and-one-shot-body
// - nodejs.core.fetch-loopback-method-query-headers-and-body
// - nodejs.core.fetch-http-error-response-versus-network-rejection
// - nodejs.core.fetch-redirect-follow-manual-and-error-modes
// - nodejs.core.fetch-content-encoding-transparent-decompression-and-body-stream
// - nodejs.core.fetch-set-cookie-access-and-no-implicit-cookie-jar
// - nodejs.core.fetch-pre-aborted-signal-propagates-reason

import assert from 'node:assert/strict';
import { gzipSync } from 'node:zlib';
import { createServer } from 'node:http';
import test from 'node:test';

let server;
let baseURL;

async function readRequestBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return Buffer.concat(chunks);
}

function sendJSON(response, value, statusCode = 200, headers = {}) {
  response.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    ...headers,
  });
  response.end(JSON.stringify(value));
}

test.before(async () => {
  server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url, 'http://loopback.invalid');

      if (url.pathname === '/echo') {
        const body = await readRequestBody(request);
        sendJSON(response, {
          method: request.method,
          pathname: url.pathname,
          query: [...url.searchParams],
          headers: request.headers,
          body: body.toString(),
        });
        return;
      }

      if (url.pathname === '/missing') {
        sendJSON(response, { found: false }, 404);
        return;
      }

      if (url.pathname === '/redirect') {
        response.writeHead(302, { location: '/final' });
        response.end();
        return;
      }

      if (url.pathname === '/final') {
        sendJSON(response, { redirected: true });
        return;
      }

      if (url.pathname === '/gzip') {
        const compressed = gzipSync(JSON.stringify({ compressed: true }));
        response.writeHead(200, {
          'content-encoding': 'gzip',
          'content-length': compressed.length,
          'content-type': 'application/json',
        });
        response.end(compressed);
        return;
      }

      if (url.pathname === '/stream') {
        response.writeHead(200, { 'content-type': 'text/plain' });
        response.write('first:');
        queueMicrotask(() => response.end('second'));
        return;
      }

      if (url.pathname === '/cookies') {
        response.writeHead(200, {
          'set-cookie': ['theme=dark; Path=/', 'session=abc; HttpOnly'],
        });
        response.end('cookies');
        return;
      }

      if (url.pathname === '/multipart') {
        const body = await readRequestBody(request);
        sendJSON(response, {
          contentType: request.headers['content-type'],
          body: body.toString(),
        });
        return;
      }

      response.writeHead(500);
      response.end('unexpected route');
    } catch (error) {
      response.writeHead(500);
      response.end(String(error));
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  assert.notEqual(address, null);
  assert.equal(typeof address, 'object');
  baseURL = `http://127.0.0.1:${address.port}`;
});

test.after(async () => {
  await new Promise((resolve, reject) => {
    server.close((error) => error === undefined ? resolve() : reject(error));
  });
});

test('Headers 规范化名称和值，并区别 append、set 与多条 Set-Cookie', () => {
  const headers = new Headers({
    Accept: ' text/plain ',
    'X-Language': 'JavaScript',
  });
  headers.append('x-language', 'Node.js');
  headers.set('x-count', '2');

  assert.equal(headers.get('ACCEPT'), 'text/plain');
  assert.equal(headers.get('X-Language'), 'JavaScript, Node.js');
  assert.equal(headers.has('x-count'), true);
  headers.delete('x-count');
  assert.equal(headers.has('x-count'), false);
  assert.deepEqual([...headers.keys()], ['accept', 'x-language']);

  headers.append('set-cookie', 'first=1; Path=/');
  headers.append('Set-Cookie', 'second=2; HttpOnly');
  assert.deepEqual(headers.getSetCookie(), [
    'first=1; Path=/',
    'second=2; HttpOnly',
  ]);
  assert.equal(headers.get('set-cookie'), 'first=1; Path=/, second=2; HttpOnly');

  assert.throws(() => headers.set('bad header', 'value'), TypeError);
  assert.throws(() => headers.set('x-value', 'line\nfeed'), TypeError);
  // 多数同名头可用逗号合并；Set-Cookie 内也可能含逗号，必须用
  // getSetCookie() 分条读取。
});

test('Blob 转换字节、文本、切片和流，File 额外携带元数据', async () => {
  const blob = new Blob([
    new Uint8Array([0x41, 0x42]),
    '中文',
  ], { type: 'Text/Plain; Charset=UTF-8' });

  assert.equal(blob.type, 'text/plain; charset=utf-8');
  assert.equal(blob.size, 8);
  assert.deepEqual([...await blob.bytes()], [0x41, 0x42, 0xe4, 0xb8, 0xad, 0xe6, 0x96, 0x87]);
  assert.deepEqual(
    [...new Uint8Array(await blob.arrayBuffer())],
    [0x41, 0x42, 0xe4, 0xb8, 0xad, 0xe6, 0x96, 0x87],
  );
  assert.equal(await blob.slice(2, 5, 'text/custom').text(), '中');
  assert.equal(await new Response(blob.stream()).text(), 'AB中文');

  const file = new File([blob], 'lesson.txt', {
    lastModified: 1_700_000_000_000,
    type: blob.type,
  });
  assert.ok(file instanceof Blob);
  assert.equal(file.name, 'lesson.txt');
  assert.equal(file.lastModified, 1_700_000_000_000);
  assert.equal(file.type, 'text/plain; charset=utf-8');
  assert.equal(await file.text(), 'AB中文');
  // Blob/File 按字节计 size，不按 JavaScript 字符数；中文 UTF-8 字符
  // 各占三个字节。
});

test('FormData 保留多值，由 fetch 生成 multipart 边界', async () => {
  const form = new FormData();
  form.append('tag', 'node');
  form.append('tag', 'web');
  form.append('temporary', 'remove me');
  form.set('title', '学习');
  form.set('title', 'Node.js');
  form.delete('temporary');
  const file = new File(['file body'], 'notes.txt', { type: 'text/plain' });
  form.append('attachment', file);

  assert.deepEqual(form.getAll('tag'), ['node', 'web']);
  assert.equal(form.get('title'), 'Node.js');
  assert.equal(form.has('temporary'), false);
  assert.equal(form.get('attachment').name, 'notes.txt');
  assert.deepEqual([...form.keys()], ['tag', 'tag', 'title', 'attachment']);

  const response = await fetch(`${baseURL}/multipart`, {
    method: 'POST',
    body: form,
  });
  const received = await response.json();
  assert.match(received.contentType, /^multipart\/form-data; boundary=/);
  assert.match(received.body, /name="tag"\r\n\r\nnode/);
  assert.match(received.body, /name="tag"\r\n\r\nweb/);
  assert.match(received.body, /name="title"\r\n\r\nNode\.js/);
  assert.match(received.body, /name="attachment"; filename="notes\.txt"/);
  assert.match(received.body, /Content-Type: text\/plain/);
  assert.match(received.body, /file body/);
  // 不要手写 Content-Type：fetch 需要把随机 boundary 同时写进头部与正文。
});

test('Request 的正文只能消费一次，clone 必须发生在读取之前', async () => {
  const request = new Request(`${baseURL}/echo`, {
    method: 'POST',
    headers: { 'content-type': 'text/plain' },
    body: 'payload',
  });
  const clone = request.clone();

  assert.equal(request.method, 'POST');
  assert.equal(request.bodyUsed, false);
  assert.equal(await request.text(), 'payload');
  assert.equal(request.bodyUsed, true);
  await assert.rejects(request.text(), TypeError);
  assert.equal(await clone.text(), 'payload');
  assert.throws(() => request.clone(), TypeError);

  assert.throws(
    () => new Request(baseURL, { method: 'GET', body: 'not allowed' }),
    TypeError,
  );
});

test('流式上传必须声明 duplex half，服务端仍按普通请求流读取', async () => {
  const body = () => new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('streamed '));
      controller.enqueue(new TextEncoder().encode('upload'));
      controller.close();
    },
  });

  assert.throws(
    () => new Request(`${baseURL}/echo`, { method: 'POST', body: body() }),
    /duplex option is required/i,
  );

  const response = await fetch(new Request(`${baseURL}/echo`, {
    method: 'POST',
    body: body(),
    duplex: 'half',
  }));
  const received = await response.json();
  assert.equal(received.body, 'streamed upload');
  assert.equal(received.headers['transfer-encoding'], 'chunked');
  // Node 的 half 目前表示先完成上传再处理响应，不等同于浏览器可用的
  // 全双工 HTTP API。
});

test('Response 工厂、clone 与 bodyUsed 明确区分元数据和一次性正文', async () => {
  const response = Response.json(
    { answer: 42 },
    { status: 201, headers: { 'x-created': 'yes' } },
  );
  const clone = response.clone();

  assert.equal(response.status, 201);
  assert.equal(response.ok, true);
  assert.equal(response.headers.get('content-type'), 'application/json');
  assert.equal(response.headers.get('x-created'), 'yes');
  assert.deepEqual(await response.json(), { answer: 42 });
  assert.equal(response.bodyUsed, true);
  await assert.rejects(response.text(), TypeError);
  assert.equal(await clone.text(), '{"answer":42}');

  const redirect = Response.redirect('https://example.test/next', 307);
  assert.equal(redirect.status, 307);
  assert.equal(redirect.headers.get('location'), 'https://example.test/next');
  assert.equal(redirect.type, 'default');

  const error = Response.error();
  assert.equal(error.status, 0);
  assert.equal(error.ok, false);
  assert.equal(error.type, 'error');
  assert.throws(() => new Response('body', { status: 204 }), TypeError);
});

test('fetch 返回 HTTP 错误响应，只拒绝传输失败', async () => {
  const response = await fetch(`${baseURL}/echo?topic=fetch&tag=a&tag=b`, {
    headers: { 'x-example': 'value' },
  });
  assert.equal(response.ok, true);
  assert.equal(response.status, 200);
  assert.equal(response.url, `${baseURL}/echo?topic=fetch&tag=a&tag=b`);
  const received = await response.json();
  assert.equal(received.method, 'GET');
  assert.deepEqual(received.query, [
    ['topic', 'fetch'],
    ['tag', 'a'],
    ['tag', 'b'],
  ]);
  assert.equal(received.headers['x-example'], 'value');

  const missing = await fetch(`${baseURL}/missing`);
  assert.equal(missing.status, 404);
  assert.equal(missing.ok, false);
  assert.deepEqual(await missing.json(), { found: false });
  // 404/500 不是网络错误；调用者必须检查 ok 或 status，不能只依赖 catch。
});

test('redirect 选项分别跟随、暴露或拒绝重定向', async () => {
  const followed = await fetch(`${baseURL}/redirect`);
  assert.equal(followed.redirected, true);
  assert.equal(followed.url, `${baseURL}/final`);
  assert.deepEqual(await followed.json(), { redirected: true });

  const manual = await fetch(`${baseURL}/redirect`, { redirect: 'manual' });
  assert.equal(manual.status, 302);
  assert.equal(manual.redirected, false);
  assert.equal(manual.headers.get('location'), '/final');

  await assert.rejects(
    fetch(`${baseURL}/redirect`, { redirect: 'error' }),
    TypeError,
  );
});

test('fetch 自动解压，response.body 仍可逐块读取', async () => {
  const compressed = await fetch(`${baseURL}/gzip`);
  assert.equal(compressed.headers.get('content-encoding'), 'gzip');
  assert.deepEqual(await compressed.json(), { compressed: true });

  const streamed = await fetch(`${baseURL}/stream`);
  assert.ok(streamed.body instanceof ReadableStream);
  const reader = streamed.body.getReader();
  const decoder = new TextDecoder();
  let text = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
  }
  text += decoder.decode();
  assert.equal(text, 'first:second');
  assert.equal(streamed.bodyUsed, true);
  // 解压在返回 Response 前由 fetch 完成，但头部仍反映线上响应，不能拿
  // content-length 当作解压后正文长度。
});

test('Set-Cookie 可逐条读取，但 fetch 不会自动维护 Cookie jar', async () => {
  const cookieResponse = await fetch(`${baseURL}/cookies`);
  assert.deepEqual(cookieResponse.headers.getSetCookie(), [
    'theme=dark; Path=/',
    'session=abc; HttpOnly',
  ]);

  const nextResponse = await fetch(`${baseURL}/echo`);
  const received = await nextResponse.json();
  assert.equal(received.headers.cookie, undefined);
  // 服务端程序若要保持会话，必须显式解析、存储并在后续请求设置
  // Cookie 头。
});

test('预先中止的 signal 让 fetch 直接以原始 reason 拒绝', async () => {
  const reason = new Error('request cancelled by caller');
  const signal = AbortSignal.abort(reason);

  await assert.rejects(
    fetch(`${baseURL}/echo`, { signal }),
    (error) => error === reason,
  );
  assert.equal(signal.reason, reason);
  // 自定义 reason 会原样传播；若只调用 abort()，常见结果则是名为
  // AbortError 的 DOMException。
});
