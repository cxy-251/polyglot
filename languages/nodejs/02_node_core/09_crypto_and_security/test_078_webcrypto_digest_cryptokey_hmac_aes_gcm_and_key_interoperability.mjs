// polyglot-covers:
// - nodejs.core.webcrypto-global-and-node-crypto-entry-points
// - nodejs.core.webcrypto-subtle-digest-array-buffer
// - nodejs.core.webcrypto-cryptokey-type-algorithm-extractable-and-usages
// - nodejs.core.webcrypto-hmac-generate-sign-and-verify
// - nodejs.core.webcrypto-secret-key-raw-and-jwk-export-import
// - nodejs.core.webcrypto-non-extractable-key-export-rejection
// - nodejs.core.webcrypto-aes-gcm-encrypt-decrypt-additional-data-and-tag
// - nodejs.core.webcrypto-aes-gcm-tamper-operation-error
// - nodejs.core.webcrypto-key-usage-enforcement
// - nodejs.core.webcrypto-keyobject-and-cryptokey-interoperability

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  KeyObject,
  createSecretKey,
  webcrypto,
} from 'node:crypto';

const { subtle } = webcrypto;
const encoder = new TextEncoder();
const decoder = new TextDecoder();

test('globalThis.crypto 与 node:crypto.webcrypto 提供同一套浏览器兼容接口', () => {
  assert.equal(globalThis.crypto, webcrypto);
  assert.equal(globalThis.crypto.subtle, subtle);
  assert.equal(typeof crypto.getRandomValues, 'function');
  assert.equal(typeof crypto.randomUUID, 'function');
  assert.equal(webcrypto.CryptoKey, undefined);
  // Node 提供 CryptoKey 实例，但没有把构造器挂到 globalThis 或 webcrypto namespace。
});

test('subtle.digest 总是异步返回 ArrayBuffer，算法名称不区分大小写', async () => {
  let sameStack = true;
  const pending = subtle.digest('sha-256', encoder.encode('abc')).then((digest) => ({
    digest,
    sameStack,
  }));
  sameStack = false;
  const { digest, sameStack: settledSynchronously } = await pending;

  assert.equal(settledSynchronously, false);
  assert.ok(digest instanceof ArrayBuffer);
  assert.equal(
    Buffer.from(digest).toString('hex'),
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
  );
  await assert.rejects(
    subtle.digest('not-a-digest', new Uint8Array()),
    (error) => error.name === 'NotSupportedError',
  );
});

test('CryptoKey 元数据描述可导出性和用途，授权能力在内部创建时固定', async () => {
  const key = await subtle.generateKey(
    { name: 'HMAC', hash: 'SHA-256', length: 256 },
    true,
    ['sign', 'verify'],
  );
  assert.equal(Object.prototype.toString.call(key), '[object CryptoKey]');
  assert.equal(key.constructor.name, 'CryptoKey');
  assert.equal(key.type, 'secret');
  assert.equal(key.extractable, true);
  assert.deepEqual(key.algorithm, { name: 'HMAC', length: 256, hash: { name: 'SHA-256' } });
  assert.deepEqual(key.usages, ['sign', 'verify']);

  const data = encoder.encode('permission metadata');
  const signature = await subtle.sign('HMAC', key, data);
  const usages = key.usages;
  usages.pop();
  assert.equal(key.usages, usages);
  assert.deepEqual(key.usages, ['sign']);
  assert.equal(await subtle.verify('HMAC', key, signature, data), true);
  // Node 24.18 暴露的 usages 数组本身可改，但授权检查不读取这个可变数组；
  // 修改它既不能可靠撤销也不能授予能力，应把 CryptoKey 当不可变 capability 使用。
});

test('HMAC sign/verify 返回 ArrayBuffer/boolean，消息改变时正常返回 false', async () => {
  const key = await subtle.generateKey(
    { name: 'HMAC', hash: 'SHA-256' },
    true,
    ['sign', 'verify'],
  );
  const data = encoder.encode('authenticated message');
  const signature = await subtle.sign('HMAC', key, data);
  assert.ok(signature instanceof ArrayBuffer);
  assert.equal(signature.byteLength, 32);
  assert.equal(await subtle.verify('HMAC', key, signature, data), true);
  assert.equal(
    await subtle.verify('HMAC', key, signature, encoder.encode('changed')),
    false,
  );
});

test('可提取 secret CryptoKey 可用 raw/JWK 往返并保留算法与用途', async () => {
  const original = await subtle.importKey(
    'raw',
    Buffer.alloc(32, 0x11),
    { name: 'HMAC', hash: 'SHA-256' },
    true,
    ['sign', 'verify'],
  );
  const raw = await subtle.exportKey('raw', original);
  const jwk = await subtle.exportKey('jwk', original);
  assert.ok(raw instanceof ArrayBuffer);
  assert.deepEqual(Buffer.from(raw), Buffer.alloc(32, 0x11));
  assert.deepEqual(
    { kty: jwk.kty, alg: jwk.alg, ext: jwk.ext, keyOps: jwk.key_ops },
    { kty: 'oct', alg: 'HS256', ext: true, keyOps: ['sign', 'verify'] },
  );

  const imported = await subtle.importKey(
    'jwk',
    jwk,
    { name: 'HMAC', hash: 'SHA-256' },
    true,
    ['verify'],
  );
  assert.deepEqual(imported.usages, ['verify']);
  assert.deepEqual(Buffer.from(await subtle.exportKey('raw', imported)), Buffer.alloc(32, 0x11));
});

test('non-extractable CryptoKey 可执行授权操作，但 exportKey 被拒绝', async () => {
  const key = await subtle.generateKey(
    { name: 'AES-GCM', length: 128 },
    false,
    ['encrypt'],
  );
  assert.equal(key.extractable, false);
  await assert.rejects(
    subtle.exportKey('raw', key),
    (error) => error.name === 'InvalidAccessError',
  );
  const encrypted = await subtle.encrypt(
    { name: 'AES-GCM', iv: new Uint8Array(12) },
    key,
    encoder.encode('allowed operation'),
  );
  assert.ok(encrypted.byteLength > 0);
});

test('AES-GCM 结果把 auth tag 附在密文尾部，additionalData 也被认证', async () => {
  const key = await subtle.generateKey(
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
  const iv = Uint8Array.from({ length: 12 }, (_, index) => index);
  const additionalData = encoder.encode('header:v1');
  const plaintext = encoder.encode('web crypto payload');
  const algorithm = { name: 'AES-GCM', iv, additionalData, tagLength: 128 };
  const encrypted = await subtle.encrypt(algorithm, key, plaintext);

  assert.equal(encrypted.byteLength, plaintext.byteLength + 16);
  const decrypted = await subtle.decrypt(algorithm, key, encrypted);
  assert.equal(decoder.decode(decrypted), 'web crypto payload');
  // 与 createCipheriv 不同，Web Crypto 不单独返回 auth tag，而是把它附在 ciphertext 中。
});

test('AES-GCM 的密文或 additionalData 被篡改时以 OperationError 拒绝', async () => {
  const key = await subtle.generateKey(
    { name: 'AES-GCM', length: 128 },
    false,
    ['encrypt', 'decrypt'],
  );
  const iv = new Uint8Array(12);
  const additionalData = encoder.encode('metadata');
  const encrypted = new Uint8Array(await subtle.encrypt(
    { name: 'AES-GCM', iv, additionalData },
    key,
    encoder.encode('payload'),
  ));
  encrypted[0] ^= 1;
  await assert.rejects(
    subtle.decrypt({ name: 'AES-GCM', iv, additionalData }, key, encrypted),
    (error) => error.name === 'OperationError',
  );
  await assert.rejects(
    subtle.decrypt(
      { name: 'AES-GCM', iv, additionalData: encoder.encode('changed') },
      key,
      await subtle.encrypt(
        { name: 'AES-GCM', iv, additionalData },
        key,
        encoder.encode('payload'),
      ),
    ),
    (error) => error.name === 'OperationError',
  );
});

test('CryptoKey.usages 会在运行时拒绝未授权操作', async () => {
  const decryptOnly = await subtle.importKey(
    'raw',
    Buffer.alloc(16, 0x22),
    'AES-GCM',
    false,
    ['decrypt'],
  );
  await assert.rejects(
    subtle.encrypt({ name: 'AES-GCM', iv: new Uint8Array(12) }, decryptOnly, new Uint8Array()),
    (error) => error.name === 'InvalidAccessError',
  );
});

test('KeyObject 与 CryptoKey 可转换并保持同一份对称密钥材料', async () => {
  const keyObject = createSecretKey(Buffer.alloc(32, 0x33));
  const cryptoKey = keyObject.toCryptoKey(
    { name: 'HMAC', hash: 'SHA-256' },
    true,
    ['sign'],
  );
  assert.equal(Object.prototype.toString.call(cryptoKey), '[object CryptoKey]');
  assert.equal(KeyObject.from(cryptoKey).equals(keyObject), true);
  const signature = await subtle.sign('HMAC', cryptoKey, encoder.encode('message'));
  assert.equal(signature.byteLength, 32);
});
