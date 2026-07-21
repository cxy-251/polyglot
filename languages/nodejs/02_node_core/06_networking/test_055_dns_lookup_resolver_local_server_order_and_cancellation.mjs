// polyglot-covers:
// - nodejs.core.dns-callback-and-promises-lookup
// - nodejs.core.dns-lookup-literal-and-all-results
// - nodejs.core.dns-lookup-versus-resolve
// - nodejs.core.dns-default-result-order
// - nodejs.core.dns-resolver-custom-servers
// - nodejs.core.dns-resolve4-ttl
// - nodejs.core.dns-resolver-cancel
// - nodejs.core.dns-error-codes

import assert from 'node:assert/strict';
import test from 'node:test';

import dns from 'node:dns';
import dnsPromises from 'node:dns/promises';
import dgram from 'node:dgram';
import { once } from 'node:events';
import { promisify } from 'node:util';

const lookupCallback = promisify(dns.lookup);

async function bindUdpServer(onMessage) {
  const socket = dgram.createSocket('udp4');
  socket.on('message', onMessage.bind(null, socket));
  socket.bind(0, '127.0.0.1');
  await once(socket, 'listening');
  return socket;
}

async function closeUdpSocket(socket) {
  if (!socket) return;
  const closed = once(socket, 'close');
  socket.close();
  await closed;
}

function dnsQuestionEnd(query) {
  let offset = 12;
  while (query[offset] !== 0) {
    offset += query[offset] + 1;
  }
  // 跳过名称末尾 0，以及 QTYPE、QCLASS 各两个字节。
  return offset + 1 + 4;
}

function makeAResponse(query, octets, ttl = 60) {
  const questionEnd = dnsQuestionEnd(query);
  const header = Buffer.alloc(12);
  query.copy(header, 0, 0, 2);
  header.writeUInt16BE(0x8180, 2); // response、recursion desired/available、NOERROR
  header.writeUInt16BE(1, 4);
  header.writeUInt16BE(1, 6);

  const answer = Buffer.alloc(16);
  answer.writeUInt16BE(0xc00c, 0); // 压缩指针：名称复用 question 的第 12 字节
  answer.writeUInt16BE(1, 2); // A
  answer.writeUInt16BE(1, 4); // IN
  answer.writeUInt32BE(ttl, 6);
  answer.writeUInt16BE(4, 10);
  Buffer.from(octets).copy(answer, 12);

  return Buffer.concat([header, query.subarray(12, questionEnd), answer]);
}

test('callback 与 promises lookup 都调用操作系统名称解析器', async () => {
  const callbackResult = await lookupCallback('127.0.0.1');
  assert.deepEqual(callbackResult, { address: '127.0.0.1', family: 4 });

  const all = await dnsPromises.lookup('127.0.0.1', { all: true });
  assert.deepEqual(all, [{ address: '127.0.0.1', family: 4 }]);

  // 对 IP 字面量，Node 直接返回识别出的实际地址族，family 提示不会把 IPv4
  // 强制映射成 IPv6，也不会作为输入校验器拒绝它。
  assert.deepEqual(await dnsPromises.lookup('127.0.0.1', { family: 6 }), {
    address: '127.0.0.1',
    family: 4,
  });
});

test('defaultResultOrder 是进程级设置，修改后必须恢复', () => {
  const previous = dns.getDefaultResultOrder();
  try {
    dns.setDefaultResultOrder('ipv4first');
    assert.equal(dns.getDefaultResultOrder(), 'ipv4first');
    assert.equal(dnsPromises.getDefaultResultOrder(), 'ipv4first');

    dnsPromises.setDefaultResultOrder('verbatim');
    assert.equal(dns.getDefaultResultOrder(), 'verbatim');
  } finally {
    dns.setDefaultResultOrder(previous);
  }
  // 排序只影响 lookup 的多地址结果，不改变 resolve4/resolve6 的 DNS 查询语义。
});

test('独立 Resolver 可指向本地 DNS server，resolve4 返回记录 TTL', async () => {
  let server;
  try {
    server = await bindUdpServer((socket, query, remote) => {
      const response = makeAResponse(query, [192, 0, 2, 42], 300);
      socket.send(response, remote.port, remote.address);
    });
    const resolver = new dnsPromises.Resolver();
    const { port } = server.address();
    resolver.setServers([`127.0.0.1:${port}`]);

    const records = await resolver.resolve4('learning.example', { ttl: true });
    assert.deepEqual(records, [{ address: '192.0.2.42', ttl: 300 }]);
    assert.deepEqual(resolver.getServers(), [`127.0.0.1:${port}`]);
  } finally {
    await closeUdpSocket(server);
  }

  // lookup 走操作系统 getaddrinfo，Resolver.resolve* 才会向 setServers 指定的 DNS 发包；
  // 二者名字相近，但缓存、hosts 文件和网络行为都不同。
});

test('Resolver.cancel 取消该实例全部未完成查询，并以 ECANCELLED 拒绝', async () => {
  let resolver;
  let server;
  try {
    server = await bindUdpServer(() => {
      // 收到查询就取消；不发送响应，也不靠定时器制造竞态。
      resolver.cancel();
    });
    resolver = new dnsPromises.Resolver();
    resolver.setServers([`127.0.0.1:${server.address().port}`]);

    await assert.rejects(
      resolver.resolve4('cancel.example'),
      (error) => error.code === dns.CANCELLED && error.code === 'ECANCELLED',
    );
  } finally {
    await closeUdpSocket(server);
  }
});

test('DNS flags 与错误码是命名常量，不应在业务代码硬编码数字或字符串', () => {
  assert.equal(typeof dns.ADDRCONFIG, 'number');
  assert.equal(typeof dns.V4MAPPED, 'number');
  assert.equal(typeof dns.ALL, 'number');
  assert.equal(dns.NODATA, 'ENODATA');
  assert.equal(dns.NOTFOUND, 'ENOTFOUND');
  assert.equal(dns.TIMEOUT, 'ETIMEOUT');
  assert.ok(Array.isArray(dns.getServers()));
});
