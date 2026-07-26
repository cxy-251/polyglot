// polyglot-covers:
// - nodejs.core.http-server-client-request-response
// - nodejs.core.http-incoming-message-method-url-version-and-complete
// - nodejs.core.http-normalized-headers-raw-headers-and-distinct-headers
// - nodejs.core.http-request-and-response-streaming-bodies
// - nodejs.core.http-request-and-response-trailers
// - nodejs.core.http-write-head-header-precedence
// - nodejs.core.http-header-name-and-value-validation
// - nodejs.core.http-method-status-and-parser-constants
// - nodejs.core.http-get-convenience-auto-end
// - nodejs.core.http-incoming-message-abort-signal
// - nodejs.core.http-server-symbol-async-dispose

import assert from 'node:assert/strict';
import test from 'node:test';

import http from 'node:http';
import { once } from 'node:events';

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address();
}

function collectResponse(request) {
  return new Promise((resolve, reject) => {
    request.once('error', reject);
    request.once('response', (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.once('error', reject);
      response.once('end', () => resolve({
        response,
        body: Buffer.concat(chunks),
      }));
    });
  });
}

test('HTTP request/response 暴露消息元数据、规范化头和原始头', async () => {
  let observedRequest;
  const server = http.createServer(async (request, response) => {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    observedRequest = {
      method: request.method,
      url: request.url,
      httpVersion: request.httpVersion,
      headers: request.headers,
      rawHeaders: request.rawHeaders,
      complete: request.complete,
      body: Buffer.concat(chunks).toString(),
    };

    response.statusCode = 201;
    response.statusMessage = 'Stored';
    response.setHeader('Content-Type', 'text/plain');
    response.setHeader('Set-Cookie', ['first=1', 'second=2']);
    response.end('created');
  });

  try {
    const address = await listen(server);
    const request = http.request({
      host: address.address,
      port: address.port,
      method: 'POST',
      path: '/items?draft=1',
      headers: {
        'Content-Type': 'text/plain',
        'Content-Length': Buffer.byteLength('payload'),
        'X-Request-Id': 'abc-123',
      },
    });
    const pending = collectResponse(request);
    request.end('payload');
    const { response, body } = await pending;

    assert.equal(response.statusCode, 201);
    assert.equal(response.statusMessage, 'Stored');
    assert.equal(response.headers['content-type'], 'text/plain');
    assert.deepEqual(response.headers['set-cookie'], ['first=1', 'second=2']);
    assert.deepEqual(response.headersDistinct['set-cookie'], ['first=1', 'second=2']);
    assert.ok(response.rawHeaders.includes('Content-Type'));
    assert.equal(body.toString(), 'created');
    assert.equal(response.complete, true);

    assert.equal(observedRequest.method, 'POST');
    assert.equal(observedRequest.url, '/items?draft=1');
    assert.equal(observedRequest.httpVersion, '1.1');
    assert.equal(observedRequest.headers['x-request-id'], 'abc-123');
    assert.ok(observedRequest.rawHeaders.includes('X-Request-Id'));
    assert.equal(observedRequest.complete, true);
    assert.equal(observedRequest.body, 'payload');
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('chunked 请求和响应都可在正文之后发送 trailers', async () => {
  let requestTrailers;
  const server = http.createServer(async (request, response) => {
    for await (const chunk of request) {
      assert.equal(chunk.toString(), 'request body');
    }
    requestTrailers = {
      normalized: request.trailers,
      raw: request.rawTrailers,
    };

    response.writeHead(200, {
      'Content-Type': 'text/plain',
      Trailer: 'X-Response-Checksum',
    });
    response.write('response ');
    response.addTrailers({ 'X-Response-Checksum': 'response-ok' });
    response.end('body');
  });

  try {
    const address = await listen(server);
    const request = http.request({
      host: address.address,
      port: address.port,
      method: 'POST',
      headers: { Trailer: 'X-Request-Checksum' },
    });
    const pending = collectResponse(request);
    request.write('request body');
    request.addTrailers({ 'X-Request-Checksum': 'request-ok' });
    request.end();
    const { response, body } = await pending;

    assert.equal(body.toString(), 'response body');
    assert.deepEqual(response.trailers, {
      'x-response-checksum': 'response-ok',
    });
    assert.deepEqual(response.rawTrailers, [
      'X-Response-Checksum',
      'response-ok',
    ]);
    assert.deepEqual(requestTrailers.normalized, {
      'x-request-checksum': 'request-ok',
    });
    assert.deepEqual(requestTrailers.raw, ['X-Request-Checksum', 'request-ok']);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('writeHead 的同名头覆盖 setHeader，getHeaderNames 使用小写名称', async () => {
  const server = http.createServer((request, response) => {
    response.setHeader('X-Source', 'set-header');
    response.setHeader('X-Keep', 'kept');
    assert.deepEqual(response.getHeaderNames().toSorted(), ['x-keep', 'x-source']);
    response.writeHead(202, { 'X-Source': 'write-head' });
    assert.equal(response.headersSent, true);
    response.end();
  });

  try {
    const address = await listen(server);
    const request = http.get({ host: address.address, port: address.port });
    const { response } = await collectResponse(request);
    assert.equal(response.statusCode, 202);
    assert.equal(response.headers['x-source'], 'write-head');
    assert.equal(response.headers['x-keep'], 'kept');
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('validateHeaderName/value 在写入 socket 前拒绝协议注入字符', () => {
  assert.equal(http.validateHeaderName('X-Valid-Header'), undefined);
  assert.equal(http.validateHeaderValue('X-Value', 'safe value'), undefined);
  assert.throws(
    () => http.validateHeaderName('Bad Header'),
    (error) => error.code === 'ERR_INVALID_HTTP_TOKEN',
  );
  assert.throws(
    () => http.validateHeaderValue('X-Value', 'line one\r\nInjected: yes'),
    (error) => error.code === 'ERR_INVALID_CHAR',
  );

  assert.ok(http.METHODS.includes('GET'));
  assert.equal(http.STATUS_CODES[404], 'Not Found');
  assert.ok(http.maxHeaderSize > 0);
});

test('http.get 自动 end 请求，适合没有请求正文的简单 GET', async () => {
  let requestEnded = false;
  const server = http.createServer((request, response) => {
    request.on('end', () => {
      requestEnded = true;
      response.end(request.url);
    });
    request.resume();
  });

  try {
    const address = await listen(server);
    const request = http.get({
      host: address.address,
      port: address.port,
      path: '/automatic-end',
    });
    const { body } = await collectResponse(request);
    assert.equal(body.toString(), '/automatic-end');
    assert.equal(requestEnded, true);
    assert.equal(request.writableEnded, true);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('IncomingMessage.signal 在客户端提前断开时中止下游工作', async () => {
  let deliverRequest;
  const incomingRequest = new Promise((resolve) => {
    deliverRequest = resolve;
  });
  const server = http.createServer((request) => {
    request.resume();
    deliverRequest(request);
  });

  try {
    const address = await listen(server);
    const client = http.request({
      host: address.address,
      port: address.port,
      method: 'POST',
    });
    client.on('error', () => undefined);
    client.write('partial body');
    client.flushHeaders();

    const request = await incomingRequest;
    const aborted = once(request.signal, 'abort');
    assert.equal(request.signal.aborted, false);
    client.destroy(new Error('caller disconnected'));
    await aborted;

    assert.equal(request.signal.aborted, true);
    assert.equal(request.signal.reason.name, 'AbortError');
    assert.equal(request.destroyed, true);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});
