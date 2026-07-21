// polyglot-covers:
// - nodejs.core.http-agent-keep-alive-and-socket-reuse
// - nodejs.core.http-client-request-reused-socket
// - nodejs.core.http-expect-100-continue
// - nodejs.core.http-check-continue-and-write-continue
// - nodejs.core.http-early-hints-and-information-event
// - nodejs.core.http-upgrade-and-should-upgrade-callback
// - nodejs.core.http-connect-tunnel
// - nodejs.core.http-max-requests-per-socket-and-drop-request
// - nodejs.core.http-client-error-parser-boundary
// - nodejs.core.http-agent-destroy

import assert from 'node:assert/strict';
import test from 'node:test';

import http from 'node:http';
import net from 'node:net';
import { once } from 'node:events';

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address();
}

function getWithRequest(options) {
  return new Promise((resolve, reject) => {
    const request = http.get(options, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.once('error', reject);
      response.once('end', () => resolve({
        request,
        response,
        body: Buffer.concat(chunks),
      }));
    });
    request.once('error', reject);
  });
}

test('keepAlive Agent 复用空闲 socket，ClientRequest 标记 reusedSocket', async () => {
  const peerPorts = [];
  let connections = 0;
  const server = http.createServer((request, response) => {
    peerPorts.push(request.socket.remotePort);
    response.end(request.url);
  });
  server.on('connection', () => {
    connections += 1;
  });
  const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });

  try {
    const address = await listen(server);
    const base = {
      host: address.address,
      port: address.port,
      agent,
    };
    const first = await getWithRequest({ ...base, path: '/first' });
    const second = await getWithRequest({ ...base, path: '/second' });

    assert.equal(first.request.reusedSocket, false);
    assert.equal(second.request.reusedSocket, true);
    assert.equal(first.body.toString(), '/first');
    assert.equal(second.body.toString(), '/second');
    assert.equal(connections, 1);
    assert.equal(peerPorts[0], peerPorts[1]);
    assert.ok(Object.keys(agent.freeSockets).length >= 1);
  } finally {
    agent.destroy();
    await server[Symbol.asyncDispose]();
  }
  // Agent 的内部字典使用 null prototype，按键数量检查比和普通 {} 深比较准确。
  assert.equal(Object.keys(agent.sockets).length, 0);
});

test('Expect: 100-continue 让客户端收到许可后再发送大正文', async () => {
  let checkContinueCalls = 0;
  const server = http.createServer();
  server.on('checkContinue', async (request, response) => {
    checkContinueCalls += 1;
    response.writeContinue();
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    response.end(`received:${Buffer.concat(chunks)}`);
  });

  try {
    const address = await listen(server);
    const request = http.request({
      host: address.address,
      port: address.port,
      method: 'POST',
      headers: {
        Expect: '100-continue',
        'Content-Length': Buffer.byteLength('payload'),
      },
    });
    const continued = once(request, 'continue');
    const response = new Promise((resolve, reject) => {
      request.once('error', reject);
      request.once('response', (incoming) => {
        const chunks = [];
        incoming.on('data', (chunk) => chunks.push(chunk));
        incoming.once('end', () => resolve(Buffer.concat(chunks).toString()));
      });
    });
    request.flushHeaders();
    await continued;
    request.end('payload');

    assert.equal(await response, 'received:payload');
    assert.equal(checkContinueCalls, 1);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('writeEarlyHints 发送 103，客户端用 information 事件接收临时响应', async () => {
  const server = http.createServer((request, response) => {
    response.writeEarlyHints({
      link: '</style.css>; rel=preload; as=style',
    });
    response.end('final response');
  });

  try {
    const address = await listen(server);
    const request = http.request({ host: address.address, port: address.port });
    const information = [];
    request.on('information', (info) => information.push(info));
    const response = new Promise((resolve) => {
      request.once('response', (incoming) => {
        incoming.resume();
        incoming.once('end', () => resolve(incoming));
      });
    });
    request.end();
    const incoming = await response;

    assert.equal(information.length, 1);
    assert.equal(information[0].statusCode, 103);
    assert.equal(information[0].headers.link, '</style.css>; rel=preload; as=style');
    assert.equal(incoming.statusCode, 200);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('upgrade 事件把 HTTP socket 移交给自定义双向协议', async () => {
  const server = http.createServer({
    shouldUpgradeCallback(request) {
      return request.headers.upgrade === 'polyglot-echo';
    },
  });
  server.on('upgrade', (request, socket, head) => {
    assert.equal(request.url, '/upgrade');
    assert.equal(head.length, 0);
    socket.write([
      'HTTP/1.1 101 Switching Protocols',
      'Connection: Upgrade',
      'Upgrade: polyglot-echo',
      '',
      '',
    ].join('\r\n'));
    socket.once('data', (chunk) => socket.end(`echo:${chunk}`));
  });

  try {
    const address = await listen(server);
    const request = http.request({
      host: address.address,
      port: address.port,
      path: '/upgrade',
      headers: {
        Connection: 'Upgrade',
        Upgrade: 'polyglot-echo',
      },
    });
    request.end();
    const [response, socket, head] = await once(request, 'upgrade');
    assert.equal(response.statusCode, 101);
    assert.equal(response.headers.upgrade, 'polyglot-echo');
    assert.equal(head.length, 0);

    const echoed = once(socket, 'data');
    const closed = once(socket, 'close');
    socket.write('ping');
    assert.equal((await echoed)[0].toString(), 'echo:ping');
    await closed;
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('CONNECT 事件可建立 HTTP 代理隧道，之后直接操作原始 socket', async () => {
  const server = http.createServer();
  server.on('connect', (request, socket, head) => {
    assert.equal(request.url, 'service.internal:443');
    assert.equal(head.length, 0);
    socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    socket.once('data', (chunk) => socket.end(`tunnel:${chunk}`));
  });

  try {
    const address = await listen(server);
    const request = http.request({
      host: address.address,
      port: address.port,
      method: 'CONNECT',
      path: 'service.internal:443',
    });
    request.end();
    const [response, socket, head] = await once(request, 'connect');
    assert.equal(response.statusCode, 200);
    assert.equal(head.length, 0);

    const tunneled = once(socket, 'data');
    const closed = once(socket, 'close');
    socket.write('encrypted bytes');
    assert.equal((await tunneled)[0].toString(), 'tunnel:encrypted bytes');
    await closed;
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('maxRequestsPerSocket 对同一连接的后续流水线请求返回 503', async () => {
  let dropped = 0;
  const server = http.createServer((request, response) => response.end(request.url));
  server.maxRequestsPerSocket = 1;
  server.on('dropRequest', () => {
    dropped += 1;
  });

  try {
    const address = await listen(server);
    const client = net.createConnection(address.port, address.address);
    await once(client, 'connect');
    const chunks = [];
    const bothResponses = new Promise((resolve) => {
      client.on('data', (chunk) => {
        chunks.push(chunk);
        if (Buffer.concat(chunks).includes('503 Service Unavailable')) resolve();
      });
    });
    const closed = once(client, 'close');
    client.write([
      'GET /first HTTP/1.1',
      'Host: localhost',
      '',
      'GET /second HTTP/1.1',
      'Host: localhost',
      '',
      '',
    ].join('\r\n'));
    await bothResponses;
    const raw = Buffer.concat(chunks).toString();
    // 不等待 keep-alive 空闲超时；拿到要验证的两份响应后主动释放测试连接。
    client.destroy();
    await closed;

    assert.match(raw, /HTTP\/1\.1 200 OK/);
    assert.match(raw, /HTTP\/1\.1 503 Service Unavailable/);
    assert.equal(dropped, 1);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('clientError 暴露 HTTP parser 错误，监听者负责发送并关闭 400', async () => {
  const parserErrors = [];
  const server = http.createServer();
  server.on('clientError', (error, socket) => {
    parserErrors.push(error);
    socket.end([
      'HTTP/1.1 400 Bad Request',
      'Connection: close',
      'Content-Length: 0',
      '',
      '',
    ].join('\r\n'));
  });

  try {
    const address = await listen(server);
    const client = net.createConnection(address.port, address.address);
    await once(client, 'connect');
    const chunks = [];
    client.on('data', (chunk) => chunks.push(chunk));
    client.write([
      'GET / HTTP/1.1',
      'Host: localhost',
      'Invalid Header: value',
      '',
      '',
    ].join('\r\n'));
    await once(client, 'end');

    assert.match(Buffer.concat(chunks).toString(), /^HTTP\/1\.1 400 Bad Request/);
    assert.equal(parserErrors.length, 1);
    assert.equal(parserErrors[0].code, 'HPE_INVALID_HEADER_TOKEN');
    assert.ok(Buffer.isBuffer(parserErrors[0].rawPacket));
  } finally {
    await server[Symbol.asyncDispose]();
  }
});
