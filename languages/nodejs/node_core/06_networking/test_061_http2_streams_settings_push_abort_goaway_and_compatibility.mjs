// polyglot-covers:
// - nodejs.core.http2-client-server-session-and-stream
// - nodejs.core.http2-pseudo-headers-and-sensitive-headers
// - nodejs.core.http2-request-response-body-and-trailers
// - nodejs.core.http2-compatibility-request-response-api
// - nodejs.core.http2-default-packed-and-unpacked-settings
// - nodejs.core.http2-server-push-stream
// - nodejs.core.http2-session-settings-and-ping
// - nodejs.core.http2-request-abort-signal-and-rst-code
// - nodejs.core.http2-forbidden-connection-headers
// - nodejs.core.http2-goaway-and-new-stream-boundary
// - nodejs.core.http2-constants-and-error-codes

import assert from 'node:assert/strict';
import test from 'node:test';

import http2 from 'node:http2';
import { once } from 'node:events';

const {
  HTTP2_HEADER_AUTHORIZATION,
  HTTP2_HEADER_METHOD,
  HTTP2_HEADER_PATH,
  HTTP2_HEADER_STATUS,
  HTTP2_METHOD_GET,
  NGHTTP2_CANCEL,
  NGHTTP2_NO_ERROR,
} = http2.constants;

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address();
}

function createServer(...arguments_) {
  const server = http2.createServer(...arguments_);
  const sessions = new Set();
  server.on('session', (session) => {
    sessions.add(session);
    session.once('close', () => sessions.delete(session));
  });
  server.destroySessions = () => {
    for (const session of sessions) session.destroy();
  };
  return server;
}

async function closeServer(server) {
  if (!server) return;
  // server.close 只停止 listen，并不会替应用决定何时终止仍存活的 HTTP/2 session。
  server.destroySessions();
  await server[Symbol.asyncDispose]();
}

async function closeSession(session) {
  if (!session || session.destroyed) return;
  const closed = new Promise((resolve) => session.once('close', resolve));
  // closed 只表示不再创建新 stream；GOAWAY 后底层 socket 仍可能存活。
  // 测试清理阶段用 destroy 保证立即释放连接，避免 server.close 等待空闲 session。
  session.destroy();
  await closed;
}

function collectClientStream(stream, headerEvent = 'response') {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let responseHeaders;
    let trailers;
    stream.on(headerEvent, (headers) => {
      responseHeaders = headers;
    });
    stream.on('trailers', (headers) => {
      trailers = headers;
    });
    stream.on('data', (chunk) => chunks.push(chunk));
    stream.once('error', reject);
    stream.once('end', () => resolve({
      headers: responseHeaders,
      trailers,
      body: Buffer.concat(chunks),
    }));
  });
}

test('HTTP/2 stream 用伪头、敏感头、正文和 trailers 表达一次交换', async () => {
  let serverObservation;
  const server = createServer();
  server.on('stream', async (stream, headers, flags, rawHeaders) => {
    let requestTrailers;
    stream.on('trailers', (value) => {
      requestTrailers = value;
    });
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    serverObservation = {
      headers,
      flags,
      rawHeaders,
      trailers: requestTrailers,
      body: Buffer.concat(chunks).toString(),
    };

    stream.respond({
      [HTTP2_HEADER_STATUS]: 201,
      'content-type': 'text/plain',
    }, { waitForTrailers: true });
    stream.on('wantTrailers', () => {
      stream.sendTrailers({ 'x-response-checksum': 'response-ok' });
    });
    stream.end('created');
  });

  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    await once(session, 'connect');
    const headers = {
      [HTTP2_HEADER_METHOD]: 'POST',
      [HTTP2_HEADER_PATH]: '/items',
      [HTTP2_HEADER_AUTHORIZATION]: 'Bearer test-token',
      [http2.sensitiveHeaders]: [HTTP2_HEADER_AUTHORIZATION],
    };
    const stream = session.request(headers, { waitForTrailers: true });
    stream.on('wantTrailers', () => {
      stream.sendTrailers({ 'x-request-checksum': 'request-ok' });
    });
    const result = collectClientStream(stream);
    stream.end('payload');
    const response = await result;

    assert.equal(response.headers[HTTP2_HEADER_STATUS], 201);
    assert.equal(response.headers['content-type'], 'text/plain');
    assert.equal(response.body.toString(), 'created');
    assert.equal(response.trailers['x-response-checksum'], 'response-ok');

    assert.equal(serverObservation.headers[HTTP2_HEADER_METHOD], 'POST');
    assert.equal(serverObservation.headers[HTTP2_HEADER_PATH], '/items');
    assert.deepEqual(
      serverObservation.headers[http2.sensitiveHeaders],
      [HTTP2_HEADER_AUTHORIZATION],
    );
    assert.equal(serverObservation.body, 'payload');
    assert.equal(serverObservation.trailers['x-request-checksum'], 'request-ok');
    assert.ok(serverObservation.rawHeaders.includes(HTTP2_HEADER_PATH));
    assert.equal(typeof serverObservation.flags, 'number');
  } finally {
    await closeSession(session);
    await closeServer(server);
  }
});

test('compatibility API 提供类似 HTTP/1 的 request/response 流接口', async () => {
  const server = createServer((request, response) => {
    assert.ok(request instanceof http2.Http2ServerRequest);
    assert.ok(response instanceof http2.Http2ServerResponse);
    assert.equal(request.method, 'GET');
    assert.equal(request.url, '/compatibility');
    assert.equal(request.httpVersion, '2.0');
    response.writeHead(202, { 'x-mode': 'compatibility' });
    response.end('compatible');
  });

  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    const stream = session.request({
      [HTTP2_HEADER_METHOD]: HTTP2_METHOD_GET,
      [HTTP2_HEADER_PATH]: '/compatibility',
    });
    stream.end();
    const result = await collectClientStream(stream);

    assert.equal(result.headers[HTTP2_HEADER_STATUS], 202);
    assert.equal(result.headers['x-mode'], 'compatibility');
    assert.equal(result.body.toString(), 'compatible');
  } finally {
    await closeSession(session);
    await closeServer(server);
  }

  const defaults = http2.getDefaultSettings();
  const packed = http2.getPackedSettings(defaults);
  assert.ok(Buffer.isBuffer(packed));
  // 解包结果使用 null prototype，展开后比较协议字段而不是对象原型。
  assert.deepEqual({ ...http2.getUnpackedSettings(packed) }, { ...defaults });
});

test('pushStream 在主响应之外主动发送关联资源', async () => {
  const server = createServer();
  server.on('stream', (stream, headers) => {
    assert.equal(headers[HTTP2_HEADER_PATH], '/index');
    stream.pushStream({ [HTTP2_HEADER_PATH]: '/asset.css' }, (error, pushed) => {
      assert.equal(error, null);
      pushed.respond({
        [HTTP2_HEADER_STATUS]: 200,
        'content-type': 'text/css',
      });
      pushed.end('body { color: green; }');
    });
    stream.respond({ [HTTP2_HEADER_STATUS]: 200 });
    stream.end('<link rel="stylesheet" href="/asset.css">');
  });

  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    const pushedResult = new Promise((resolve, reject) => {
      session.once('stream', async (pushed, requestHeaders) => {
        try {
          // Server Push 流的响应头通过 push 事件交付，不是普通请求流的 response 事件。
          const result = await collectClientStream(pushed, 'push');
          resolve({ requestHeaders, result });
        } catch (error) {
          reject(error);
        }
      });
    });
    const main = session.request({ [HTTP2_HEADER_PATH]: '/index' });
    main.end();

    const mainResult = await collectClientStream(main);
    const pushed = await pushedResult;
    assert.match(mainResult.body.toString(), /asset\.css/);
    assert.equal(pushed.requestHeaders[HTTP2_HEADER_PATH], '/asset.css');
    assert.equal(pushed.result.headers['content-type'], 'text/css');
    assert.equal(pushed.result.body.toString(), 'body { color: green; }');
  } finally {
    await closeSession(session);
    await closeServer(server);
  }
});

test('session.settings 更新对端视角，ping 用八字节 payload 测量往返', async () => {
  const server = createServer();
  let deliverServerSession;
  const serverSessionPromise = new Promise((resolve) => {
    deliverServerSession = resolve;
  });
  server.on('session', deliverServerSession);

  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    await once(session, 'connect');
    const serverSession = await serverSessionPromise;
    const remoteSettings = once(serverSession, 'remoteSettings');
    await new Promise((resolve, reject) => {
      session.settings({ maxConcurrentStreams: 7 }, (error) => {
        if (error) reject(error);
        else resolve();
      });
    });
    await remoteSettings;
    assert.equal(serverSession.remoteSettings.maxConcurrentStreams, 7);

    const payload = Buffer.from('12345678');
    const ping = await new Promise((resolve, reject) => {
      session.ping(payload, (error, duration, echoed) => {
        if (error) reject(error);
        else resolve({ duration, echoed });
      });
    });
    assert.ok(ping.duration >= 0);
    assert.deepEqual(ping.echoed, payload);
    assert.ok(session.localSettings.headerTableSize > 0);
    assert.ok(session.remoteSettings.maxFrameSize > 0);
  } finally {
    await closeSession(session);
    await closeServer(server);
  }
});

test('AbortSignal 取消单个请求流，发送 CANCEL 而不必销毁整个 session', async () => {
  let deliverServerStream;
  const serverStreamPromise = new Promise((resolve) => {
    deliverServerStream = resolve;
  });
  const server = createServer();
  server.on('stream', (stream) => deliverServerStream(stream));

  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    const controller = new AbortController();
    const request = session.request(
      { [HTTP2_HEADER_PATH]: '/cancel' },
      { signal: controller.signal },
    );
    request.on('error', () => undefined);
    request.end();
    const serverStream = await serverStreamPromise;
    const serverAborted = once(serverStream, 'aborted');
    const requestClosed = new Promise((resolve) => request.once('close', resolve));

    controller.abort(new Error('caller cancelled'));
    await Promise.all([serverAborted, requestClosed]);
    assert.equal(request.rstCode, NGHTTP2_CANCEL);
    assert.equal(serverStream.rstCode, NGHTTP2_CANCEL);
    assert.equal(session.destroyed, false);
  } finally {
    await closeSession(session);
    await closeServer(server);
  }
});

test('HTTP/2 拒绝 connection-specific header，常量避免硬编码协议数字', async () => {
  const server = createServer();
  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    await once(session, 'connect');

    assert.throws(
      () => session.request({
        [HTTP2_HEADER_PATH]: '/',
        connection: 'keep-alive',
      }),
      (error) => error.code === 'ERR_HTTP2_INVALID_CONNECTION_HEADERS',
    );
    assert.equal(NGHTTP2_NO_ERROR, 0);
    assert.equal(NGHTTP2_CANCEL, 8);
  } finally {
    await closeSession(session);
    await closeServer(server);
  }
});

test('GOAWAY 允许已有 stream 收尾，并把 session 标记为不再接收新 stream', async () => {
  const server = createServer();
  server.on('stream', (stream) => {
    const serverSession = stream.session;
    stream.respond({ [HTTP2_HEADER_STATUS]: 200 });
    stream.end('last response');
    serverSession.goaway(
      NGHTTP2_NO_ERROR,
      stream.id,
      Buffer.from('maintenance'),
    );
    // goaway 只发送协议边界；close 才在已接受的 stream 收尾后关闭 transport。
    serverSession.close();
  });

  let session;
  try {
    const address = await listen(server);
    session = http2.connect(`http://${address.address}:${address.port}`);
    const sessionClosed = new Promise((resolve) => session.once('close', resolve));
    const goaway = once(session, 'goaway');
    const stream = session.request({ [HTTP2_HEADER_PATH]: '/last' });
    stream.end();
    const result = await collectClientStream(stream);
    const [errorCode, lastStreamID, opaqueData] = await goaway;

    assert.equal(result.body.toString(), 'last response');
    assert.equal(errorCode, NGHTTP2_NO_ERROR);
    assert.equal(lastStreamID, stream.id);
    assert.equal(opaqueData.toString(), 'maintenance');
    assert.equal(session.closed, true);
    // GOAWAY 后 session 会自动进入关闭流程；不要竞态创建一个“待分配 ID”的 stream
    // 再等待错误，而应把后续请求路由到新 session。
    await sessionClosed;
    assert.equal(session.destroyed, true);
  } finally {
    await closeSession(session);
    await closeServer(server);
  }
});
