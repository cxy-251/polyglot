// polyglot-covers:
// - nodejs.core.tls-create-secure-context
// - nodejs.core.tls-server-client-secure-connection
// - nodejs.core.tls-sni-callback-and-servername
// - nodejs.core.tls-alpn-negotiation
// - nodejs.core.tls-peer-certificate-protocol-and-cipher
// - nodejs.core.tls-export-keying-material-and-finished-messages
// - nodejs.core.tls-certificate-authority-verification
// - nodejs.core.tls-check-server-identity
// - nodejs.core.tls-custom-hostname-verifier-danger
// - nodejs.core.tls-ciphers-roots-and-version-defaults
// - nodejs.core.https-server-request-response
// - nodejs.core.https-self-signed-ca-and-authorization
// - nodejs.core.https-untrusted-certificate-error

import assert from 'node:assert/strict';
import test from 'node:test';

import https from 'node:https';
import tls from 'node:tls';
import { X509Certificate } from 'node:crypto';
import { once } from 'node:events';

// 这张 localhost 证书和私钥只供测试，二者都是公开仓库数据，绝不能用于真实服务。
// 有效期覆盖 2026-07-14 至 2126-06-20，SAN 同时包含 localhost 和 127.0.0.1。
const CERTIFICATE_PEM = `-----BEGIN CERTIFICATE-----
MIIDATCCAemgAwIBAgIJAKHGj8u9SNRwMA0GCSqGSIb3DQEBCwUAMBQxEjAQBgNV
BAMMCWxvY2FsaG9zdDAgFw0yNjA3MTQxODIxMDFaGA8yMTI2MDYyMDE4MjEwMVow
FDESMBAGA1UEAwwJbG9jYWxob3N0MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEA53IVpFEhyo3dAqeWDlbD2UK5ku5POqE/DmP7VXkQM/sRDoqmZjouzMmi
Pl8QcILjREbZ5RiT1ws1z6I8UdVQRRl6cXS0hPVu7CBMUrxPWbJc1NvOlSaaS6a4
FoTkioKE6cihSFd7DKEE9/3bI0KkboxP2nbMaTZ7ljqWDOLO6k11IEJYnzydhXp0
QhKX+LUEDBv+X3D7WYfGfNW6Vou8C14eIqoILgiq7YzY/whwaVbfiGrXgJCrjuAl
fhj9zi0xzblhhekB2hbsEkX/kJG7i34TZznKcJs0O79kYjWiTV2hzZWwVpJ1XIk6
vcZAHa+funiGq4Z2bQO0Sy4WFVB0VQIDAQABo1QwUjAPBgNVHRMBAf8EBTADAQH/
MA4GA1UdDwEB/wQEAwICpDATBgNVHSUEDDAKBggrBgEFBQcDATAaBgNVHREEEzAR
gglsb2NhbGhvc3SHBH8AAAEwDQYJKoZIhvcNAQELBQADggEBAA+vVBoThMoLXz1d
3mJQ34GyG/i2IEFr3cSIwAyRvbFZM/bfV7g2Et5rso3d6su9Cw/6xorxixY9yjQC
cu5cfY3wKNmQ1kxwuZiQeu6MBcp+uqqFAoCLr2y59wtDaQtzzZREfWCh1OI3yYKr
2SVUcHejP4GKXrQy5d2BNQd/jFrhkhMU3KBIIf6drkvgfTjMmcT3qvedjEquZiw7
veg6HzDvVYgWCp1m19d3wOBLIfKtNuzJkcGXWeg9AcncbSQwIg5W63JoikxU4eFN
dd51MUN1hZ20TQkaSP7Q/9UTKJXgrKSb1AHPYQLunVder7Ut5YTEcM/RANbGviPM
xlKyxb0=
-----END CERTIFICATE-----`;

const PRIVATE_KEY_PEM = `-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDnchWkUSHKjd0C
p5YOVsPZQrmS7k86oT8OY/tVeRAz+xEOiqZmOi7MyaI+XxBwguNERtnlGJPXCzXP
ojxR1VBFGXpxdLSE9W7sIExSvE9ZslzU286VJppLprgWhOSKgoTpyKFIV3sMoQT3
/dsjQqRujE/adsxpNnuWOpYM4s7qTXUgQlifPJ2FenRCEpf4tQQMG/5fcPtZh8Z8
1bpWi7wLXh4iqgguCKrtjNj/CHBpVt+IateAkKuO4CV+GP3OLTHNuWGF6QHaFuwS
Rf+QkbuLfhNnOcpwmzQ7v2RiNaJNXaHNlbBWknVciTq9xkAdr5+6eIarhnZtA7RL
LhYVUHRVAgMBAAECggEBANZITPs+Vp/XqokbqhWKhXdwjKoZ0+b/hYcIUJm5JaRK
zmb9PcSmF9Bo2rsOfwT8WfhL9M9kavSNn3umxFwruE7RoQjMOZpkNheOa7uqN3lf
Zw14mRKElBR4vjWzQnlvECn3JEP7IqT1q8kDEtHZkK39YK1ukiDTXacghO5XS6Wm
4IH2lKNL71vBdNFDCsmkjGwSTAg9CaNzbuWQcqHzD1LoOnqaCwV0F+SfYRAEDxgD
2gC/2vZvB3lnbnQdndv8KKCIEK77i+yxLO97PmAlN1AcYi/8JkvtkvgCcd1KQsso
EdKN8/YKETie1RMz2bqp5oUi4p8dxFcIMUzLHrPSS+ECgYEA9zbd08hQJcectTyp
BithvBhg1AOZoSxQ/tZqGmBgPpocJD3j7+NBwmlUb5kvtiz6khhGykpdCaxHLdn6
InXv71a+eRR1gQaVlE4DXBrR56VPcO+a7b9N5pQZIaRdsTIjI1f/R+6ZcaahS020
oFbOp+a4w2JDd/bRejzEpcrvAy0CgYEA76vBicn9Z43vKPiuClzx6c0U26mdd517
oAQnYonwiTFQxVEA0T/bibt0haJk0ip+OUKM3N1BZkjsPmjJnoUo2XU1m1xXnZlk
N0xWQfw/DTWh8c4fX55A4gLxqPuz752CbMMPEzXuKGJL79E9BY0Wb3rFhdtMdJZ8
lQYG3dn0jskCgYEAkLfIwfqomIUzApHBLMBmlXL79AErhUNpItWoBUrX7K3QvZKR
hdPWohWA/VeCq7XG9ZFKl49SyZ/Vh0zsdhHuZIC2PjEw3FhbZhcJNnjo2h9W0vkh
C/6KfunBkIUk598+3Kjd42EU6IgwMeIKVDadAYM6M/6pGmgdlt5OC/QxWP0CgYA+
YMSJeTHj3tQNJNQfTFuGD2NLXJToSeugFRSvF9mry1MLV+7Ph0A7U7ebBE4bSQX7
HzAMV+WqmnYqNBmtkVi1aEUgf2MqWH71yX91wxIh/QB+L7iIqWaXrE57Pa9yQNtu
NUJaLKIkjpjW/O1V4YeiUiDQmugGPBiGrL/iw9RbyQKBgDNycF1CffptAruTIx52
yPEaFlBoJ1SkZmScpNSEPo0YGVkcWnzIXUmpAD9Sk2lXffqswpFUCn2ucGKmCOSH
5oiLHD+L0fStsIGYQ/uI52kWZ6slbfj4TPV0LIYklvKV05h42V+VOa6VEjICXOsj
q2onQOhHA3N78n7lLuMG4e0n
-----END PRIVATE KEY-----`;

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address();
}

function collectHttpsResponse(request) {
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

test('TLS 回环连接完成 SNI、ALPN、证书、cipher 与 exporter 协商', async () => {
  const secureContext = tls.createSecureContext({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
    minVersion: 'TLSv1.2',
  });
  const sniNames = [];
  let deliverServerSocket;
  const serverSocketPromise = new Promise((resolve) => {
    deliverServerSocket = resolve;
  });
  const server = tls.createServer({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
    ALPNProtocols: ['h2', 'http/1.1'],
    SNICallback(servername, callback) {
      sniNames.push(servername);
      callback(null, secureContext);
    },
  }, (socket) => {
    deliverServerSocket(socket);
    socket.once('data', (chunk) => socket.end(`secure:${chunk}`));
  });
  server.on('tlsClientError', () => undefined);

  try {
    const address = await listen(server);
    const client = tls.connect({
      host: address.address,
      port: address.port,
      servername: 'localhost',
      ca: CERTIFICATE_PEM,
      ALPNProtocols: ['http/1.1'],
    });
    await once(client, 'secureConnect');
    const serverSocket = await serverSocketPromise;

    assert.equal(client.authorized, true);
    assert.equal(client.authorizationError, null);
    assert.equal(client.encrypted, true);
    assert.equal(client.alpnProtocol, 'http/1.1');
    assert.equal(serverSocket.alpnProtocol, 'http/1.1');
    assert.deepEqual(sniNames, ['localhost']);
    assert.equal(serverSocket.servername, 'localhost');
    assert.match(client.getProtocol(), /^TLSv1\.[23]$/);
    assert.equal(typeof client.getCipher().standardName, 'string');

    const peer = client.getPeerCertificate();
    assert.equal(peer.subject.CN, 'localhost');
    assert.match(peer.subjectaltname, /DNS:localhost/);
    assert.ok(client.getPeerX509Certificate() instanceof X509Certificate);

    const clientKey = client.exportKeyingMaterial(32, 'polyglot exporter');
    const serverKey = serverSocket.exportKeyingMaterial(32, 'polyglot exporter');
    assert.deepEqual(clientKey, serverKey);
    assert.deepEqual(client.getFinished(), serverSocket.getPeerFinished());

    client.setEncoding('utf8');
    const response = once(client, 'data');
    const closed = once(client, 'close');
    client.end('payload');
    assert.deepEqual(await response, ['secure:payload']);
    await closed;
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('默认不信任自签名证书，显式 CA 后仍独立校验 hostname', async () => {
  const server = tls.createServer({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
  }, (socket) => socket.end());
  server.on('tlsClientError', () => undefined);

  try {
    const address = await listen(server);
    const untrusted = tls.connect({
      host: address.address,
      port: address.port,
      servername: 'localhost',
    });
    const untrustedError = await once(untrusted, 'error');
    assert.equal(untrustedError[0].code, 'DEPTH_ZERO_SELF_SIGNED_CERT');

    const trusted = tls.connect({
      host: address.address,
      port: address.port,
      servername: 'localhost',
      ca: CERTIFICATE_PEM,
    });
    await once(trusted, 'secureConnect');
    const wrongHost = tls.checkServerIdentity(
      'wrong.example',
      trusted.getPeerCertificate(),
    );
    assert.equal(wrongHost.code, 'ERR_TLS_CERT_ALTNAME_INVALID');
    trusted.end();
    await once(trusted, 'close');
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('自定义 checkServerIdentity 返回 undefined 会绕过 hostname 不匹配', async () => {
  const checkedHosts = [];
  const server = tls.createServer({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
  }, (socket) => socket.end());

  try {
    const address = await listen(server);
    const client = tls.connect({
      host: address.address,
      port: address.port,
      servername: 'wrong.example',
      ca: CERTIFICATE_PEM,
      checkServerIdentity(hostname, certificate) {
        checkedHosts.push(hostname);
        assert.equal(
          tls.checkServerIdentity(hostname, certificate).code,
          'ERR_TLS_CERT_ALTNAME_INVALID',
        );
        return undefined;
      },
    });
    await once(client, 'secureConnect');

    assert.equal(client.authorized, true);
    assert.deepEqual(checkedHosts, ['wrong.example']);
    client.end();
    await once(client, 'close');
  } finally {
    await server[Symbol.asyncDispose]();
  }
  // 这类覆盖只适合确有其他身份校验机制的协议；随意返回 undefined 会关闭主机名防线。
});

test('TLS 模块公开构建支持的 cipher、根证书与默认协议版本', () => {
  const ciphers = tls.getCiphers();
  assert.ok(ciphers.includes('aes128-gcm-sha256'));
  assert.equal(ciphers.length, new Set(ciphers).size);
  assert.ok(tls.rootCertificates.length > 0);
  assert.equal(tls.DEFAULT_MIN_VERSION, 'TLSv1.2');
  assert.equal(tls.DEFAULT_MAX_VERSION, 'TLSv1.3');

  const certificate = new X509Certificate(CERTIFICATE_PEM);
  assert.equal(certificate.subject, 'CN=localhost');
  assert.match(certificate.subjectAltName, /DNS:localhost/);
  assert.doesNotThrow(() => tls.createSecureContext({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
  }));
});

test('HTTPS 在 HTTP 流语义下附加 TLS 授权状态', async () => {
  let serverSawEncryptedSocket = false;
  const server = https.createServer({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
  }, async (request, response) => {
    serverSawEncryptedSocket = request.socket instanceof tls.TLSSocket;
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    response.setHeader('Content-Type', 'application/json');
    response.end(JSON.stringify({
      method: request.method,
      body: Buffer.concat(chunks).toString(),
      encrypted: request.socket.encrypted,
    }));
  });

  try {
    const address = await listen(server);
    const request = https.request({
      host: address.address,
      port: address.port,
      servername: 'localhost',
      ca: CERTIFICATE_PEM,
      agent: false,
      method: 'POST',
    });
    const pending = collectHttpsResponse(request);
    request.end('https payload');
    const { response, body } = await pending;
    const value = JSON.parse(body);

    assert.equal(response.statusCode, 200);
    assert.equal(response.socket.authorized, true);
    assert.equal(response.socket.encrypted, true);
    assert.deepEqual(value, {
      method: 'POST',
      body: 'https payload',
      encrypted: true,
    });
    assert.equal(serverSawEncryptedSocket, true);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});

test('HTTPS 客户端未提供测试 CA 时拒绝响应而不是降级明文', async () => {
  const server = https.createServer({
    key: PRIVATE_KEY_PEM,
    cert: CERTIFICATE_PEM,
  }, (request, response) => response.end('must not be accepted'));
  server.on('tlsClientError', () => undefined);

  try {
    const address = await listen(server);
    const request = https.get({
      host: address.address,
      port: address.port,
      servername: 'localhost',
      agent: false,
    });
    const closed = new Promise((resolve) => request.once('close', resolve));
    const [error] = await once(request, 'error');
    assert.equal(error.code, 'DEPTH_ZERO_SELF_SIGNED_CERT');
    // error 表示验证已经失败；destroyed/close 的生命周期状态在随后才稳定。
    await closed;
    assert.equal(request.destroyed, true);
  } finally {
    await server[Symbol.asyncDispose]();
  }
});
