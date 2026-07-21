// polyglot-covers:
// - nodejs.core.net-tcp-server-client-dynamic-port
// - nodejs.core.net-socket-address-metadata
// - nodejs.core.net-server-get-connections
// - nodejs.core.net-socket-half-close
// - nodejs.core.net-ipc-unix-domain-socket
// - nodejs.core.net-is-ipv4-ipv6-and-is-ip
// - nodejs.core.net-socket-address-parse
// - nodejs.core.net-block-list-address-range-subnet-and-json
// - nodejs.core.net-server-listen-abort-signal
// - nodejs.core.net-server-symbol-async-dispose

import assert from 'node:assert/strict';
import test from 'node:test';

import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';
import net, { BlockList, SocketAddress } from 'node:net';

async function listenTcp(server, options = {}) {
  server.listen({ host: '127.0.0.1', port: 0, ...options });
  await once(server, 'listening');
  return server.address();
}

async function connectionCount(server) {
  return new Promise((resolve, reject) => {
    server.getConnections((error, count) => {
      if (error) reject(error);
      else resolve(count);
    });
  });
}

test('TCP server/client 在动态回环端口交换数据并公开两端地址', async () => {
  const serverSockets = [];
  let serverPeerAddress;
  const server = net.createServer((socket) => {
    serverSockets.push(socket);
    serverPeerAddress = socket.remoteAddress;
    socket.setEncoding('utf8');
    socket.once('data', (data) => socket.end(`echo:${data}`));
  });
  try {
    const address = await listenTcp(server);
    const client = net.createConnection({
      host: address.address,
      port: address.port,
    });
    await once(client, 'connect');

    assert.equal(address.family, 'IPv4');
    assert.equal(await connectionCount(server), 1);
    assert.equal(client.remoteAddress, '127.0.0.1');
    assert.equal(client.remotePort, address.port);
    assert.equal(client.localAddress, '127.0.0.1');
    assert.equal(typeof client.localPort, 'number');
    assert.equal(client.setNoDelay(true), client);
    assert.equal(client.setKeepAlive(true, 1_000), client);

    client.setEncoding('utf8');
    const response = once(client, 'data');
    const closed = once(client, 'close');
    client.end('hello');
    assert.deepEqual(await response, ['echo:hello']);
    await closed;

    // Socket 关闭后 remoteAddress 可能被清空；需要在连接存活时保存诊断信息。
    assert.equal(serverPeerAddress, '127.0.0.1');
    assert.equal(serverSockets[0].destroyed, true);
  } finally {
    await server[Symbol.asyncDispose]();
  }
  assert.equal(server.listening, false);
});

test('allowHalfOpen 让一侧收到 FIN 后仍可从另一侧发送尾部数据', async () => {
  const server = net.createServer({ allowHalfOpen: true });
  const address = await listenTcp(server);
  const serverSocketPromise = once(server, 'connection');
  const client = net.createConnection(address.port, address.address);
  await once(client, 'connect');
  const [serverSocket] = await serverSocketPromise;
  const receivedByServer = [];
  serverSocket.on('data', (chunk) => receivedByServer.push(chunk));

  const serverSawEnd = once(serverSocket, 'end');
  const clientData = once(client, 'data');
  client.end('request');
  await serverSawEnd;

  assert.equal(serverSocket.readableEnded, true);
  assert.equal(serverSocket.writableEnded, false);
  serverSocket.end('tail');
  assert.equal((await clientData)[0].toString(), 'tail');
  await once(client, 'close');
  assert.equal(Buffer.concat(receivedByServer).toString(), 'request');
  await server[Symbol.asyncDispose]();
});

test('Unix domain socket 用文件系统路径提供本机 IPC', async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-net-'));
  const socketPath = join(root, 'service.sock');
  const server = net.createServer((socket) => socket.end('ipc response'));

  try {
    server.listen(socketPath);
    await once(server, 'listening');
    assert.equal(server.address(), socketPath);

    const client = net.createConnection(socketPath);
    const chunks = [];
    client.on('data', (chunk) => chunks.push(chunk));
    await once(client, 'end');
    assert.equal(Buffer.concat(chunks).toString(), 'ipc response');
    await once(client, 'close');
  } finally {
    await server[Symbol.asyncDispose]();
    await rm(root, { recursive: true, force: true });
  }
});

test('IP 分类与 SocketAddress.parse 避免用字符串切割主机和端口', () => {
  assert.equal(net.isIPv4('192.0.2.1'), true);
  assert.equal(net.isIPv6('2001:db8::1'), true);
  assert.equal(net.isIP('192.0.2.1'), 4);
  assert.equal(net.isIP('2001:db8::1'), 6);
  assert.equal(net.isIP('example.com'), 0);

  const ipv4 = SocketAddress.parse('192.0.2.1:8080');
  assert.equal(ipv4.address, '192.0.2.1');
  assert.equal(ipv4.port, 8080);
  assert.equal(ipv4.family, 'ipv4');

  const ipv6 = SocketAddress.parse('[2001:db8::1]:443');
  assert.equal(ipv6.address, '2001:db8::1');
  assert.equal(ipv6.port, 443);
  assert.equal(ipv6.family, 'ipv6');
  assert.equal(SocketAddress.parse('not-an-address'), undefined);
});

test('BlockList 组合单地址、范围和子网规则，并可序列化重建', () => {
  const list = new BlockList();
  list.addAddress('192.0.2.10');
  list.addRange('198.51.100.1', '198.51.100.9');
  list.addSubnet('203.0.113.0', 24);

  assert.equal(list.check('192.0.2.10'), true);
  assert.equal(list.check('198.51.100.5'), true);
  assert.equal(list.check('203.0.113.200'), true);
  assert.equal(list.check('203.0.114.1'), false);
  assert.equal(list.check(new SocketAddress({ address: '192.0.2.10' })), true);

  const restored = new BlockList();
  restored.fromJSON(list.toJSON());
  // rules 的展示顺序与 JSON 的重建顺序不是匹配语义，不能把数组顺序当优先级。
  assert.deepEqual(restored.rules.toSorted(), list.rules.toSorted());
  assert.equal(restored.check('198.51.100.5'), true);
});

test('listen 的 AbortSignal 会停止接收新连接并关闭 server', async () => {
  const controller = new AbortController();
  const server = net.createServer();
  const closed = once(server, 'close');
  await listenTcp(server, { signal: controller.signal });

  assert.equal(server.listening, true);
  controller.abort();
  await closed;
  assert.equal(server.listening, false);
});
