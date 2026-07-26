// polyglot-covers:
// - nodejs.core.webcrypto-cryptokey-pair-public-private-types-and-usages
// - nodejs.core.webcrypto-ecdsa-sign-verify-and-p1363-signature
// - nodejs.core.webcrypto-asymmetric-spki-pkcs8-and-jwk-export-import
// - nodejs.core.webcrypto-get-public-key-from-private-key
// - nodejs.core.webcrypto-rsa-oaep-label-encrypt-and-decrypt
// - nodejs.core.webcrypto-pbkdf2-import-derive-bits-and-derive-key
// - nodejs.core.webcrypto-hkdf-derive-bits
// - nodejs.core.webcrypto-ecdh-derive-bits
// - nodejs.core.webcrypto-aes-key-wrap-and-unwrap

import assert from 'node:assert/strict';
import test from 'node:test';

import { subtle } from 'node:crypto';

const encoder = new TextEncoder();
const decoder = new TextDecoder();
const experimentalWarnings = [];
const originalEmitWarning = process.emitWarning;
process.emitWarning = function captureExperimentalWarning(warning, options, ...args) {
  const type = typeof options === 'string' ? options : options?.type;
  if (type === 'ExperimentalWarning') {
    experimentalWarnings.push(String(warning));
    return;
  }
  return originalEmitWarning.call(this, warning, options, ...args);
};
test.after(() => {
  process.emitWarning = originalEmitWarning;
});

test('ECDSA generateKey 返回用途分离的公私 CryptoKey，并产生 P1363 签名', async () => {
  const pair = await subtle.generateKey(
    { name: 'ECDSA', namedCurve: 'P-256' },
    true,
    ['sign', 'verify'],
  );
  assert.equal(pair.publicKey.type, 'public');
  assert.equal(pair.privateKey.type, 'private');
  assert.deepEqual(pair.publicKey.usages, ['verify']);
  assert.deepEqual(pair.privateKey.usages, ['sign']);
  assert.deepEqual(pair.publicKey.algorithm, { name: 'ECDSA', namedCurve: 'P-256' });

  const data = encoder.encode('ecdsa message');
  const signature = await subtle.sign(
    { name: 'ECDSA', hash: 'SHA-256' },
    pair.privateKey,
    data,
  );
  assert.equal(signature.byteLength, 64);
  assert.equal(await subtle.verify(
    { name: 'ECDSA', hash: 'SHA-256' },
    pair.publicKey,
    signature,
    data,
  ), true);
  // Web Crypto 的 P-256 ECDSA 签名是固定 64 字节 r||s，不是长度可变的 ASN.1 DER。
});

test('ECDSA 公私钥分别用 SPKI/PKCS8/JWK 往返，getPublicKey 可从私钥派生公钥', async () => {
  const pair = await subtle.generateKey(
    { name: 'ECDSA', namedCurve: 'P-256' },
    true,
    ['sign', 'verify'],
  );
  const spki = await subtle.exportKey('spki', pair.publicKey);
  const pkcs8 = await subtle.exportKey('pkcs8', pair.privateKey);
  const publicJwk = await subtle.exportKey('jwk', pair.publicKey);
  const privateJwk = await subtle.exportKey('jwk', pair.privateKey);
  assert.ok(spki instanceof ArrayBuffer);
  assert.ok(pkcs8 instanceof ArrayBuffer);
  assert.equal(publicJwk.kty, 'EC');
  assert.equal(publicJwk.crv, 'P-256');
  assert.equal('d' in publicJwk, false);
  assert.equal(typeof privateJwk.d, 'string');

  const importedPublic = await subtle.importKey(
    'spki',
    spki,
    { name: 'ECDSA', namedCurve: 'P-256' },
    true,
    ['verify'],
  );
  const importedPrivate = await subtle.importKey(
    'pkcs8',
    pkcs8,
    { name: 'ECDSA', namedCurve: 'P-256' },
    true,
    ['sign'],
  );
  const derivedPublic = await subtle.getPublicKey(importedPrivate, ['verify']);
  assert.deepEqual(
    Buffer.from(await subtle.exportKey('spki', importedPublic)),
    Buffer.from(await subtle.exportKey('spki', derivedPublic)),
  );
  assert.ok(experimentalWarnings.some((warning) => warning.includes('getPublicKey')));
  // getPublicKey 在 Node 24.18 仍是 active development API，升级版本时需重查其稳定级别。
});

test('RSA-OAEP 用 public encrypt/private decrypt，label 不匹配会以 OperationError 拒绝', async () => {
  const pair = await subtle.generateKey({
    name: 'RSA-OAEP',
    modulusLength: 1024,
    publicExponent: new Uint8Array([1, 0, 1]),
    hash: 'SHA-256',
  }, false, ['encrypt', 'decrypt']);
  const label = encoder.encode('protocol:v1');
  const encrypted = await subtle.encrypt(
    { name: 'RSA-OAEP', label },
    pair.publicKey,
    encoder.encode('short secret'),
  );
  const decrypted = await subtle.decrypt(
    { name: 'RSA-OAEP', label },
    pair.privateKey,
    encrypted,
  );
  assert.equal(decoder.decode(decrypted), 'short secret');
  await assert.rejects(
    subtle.decrypt(
      { name: 'RSA-OAEP', label: encoder.encode('protocol:v2') },
      pair.privateKey,
      encrypted,
    ),
    (error) => error.name === 'OperationError',
  );
});

test('PBKDF2 base key 不可直接使用，deriveBits 与 deriveKey 表达不同结果形态', async () => {
  const password = await subtle.importKey(
    'raw',
    encoder.encode('password'),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey'],
  );
  assert.equal(password.extractable, false);
  const parameters = {
    name: 'PBKDF2',
    salt: encoder.encode('0123456789abcdef'),
    iterations: 100,
    hash: 'SHA-256',
  };
  const bits = await subtle.deriveBits(parameters, password, 256);
  const aesKey = await subtle.deriveKey(
    parameters,
    password,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt'],
  );

  assert.equal(bits.byteLength, 32);
  assert.deepEqual(Buffer.from(await subtle.exportKey('raw', aesKey)), Buffer.from(bits));
  assert.deepEqual(aesKey.usages, ['encrypt', 'decrypt']);
  // deriveKey 等价于先 deriveBits 再 importKey，但可让中间密钥字节不暴露给 JavaScript。
});

test('HKDF base key 配合 salt/info 派生指定 bit 长度', async () => {
  const inputKey = await subtle.importKey(
    'raw',
    encoder.encode('input keying material'),
    'HKDF',
    false,
    ['deriveBits'],
  );
  const parameters = {
    name: 'HKDF',
    hash: 'SHA-256',
    salt: encoder.encode('salt'),
    info: encoder.encode('context:v1'),
  };
  const first = await subtle.deriveBits(parameters, inputKey, 256);
  const second = await subtle.deriveBits(
    { ...parameters, info: encoder.encode('context:v2') },
    inputKey,
    256,
  );
  assert.equal(first.byteLength, 32);
  assert.notDeepEqual(Buffer.from(first), Buffer.from(second));
});

test('ECDH 双方用自己的 privateKey 与对方 publicKey 派生同一秘密', async () => {
  const alice = await subtle.generateKey(
    { name: 'ECDH', namedCurve: 'P-256' },
    false,
    ['deriveBits'],
  );
  const bob = await subtle.generateKey(
    { name: 'ECDH', namedCurve: 'P-256' },
    false,
    ['deriveBits'],
  );
  const aliceSecret = await subtle.deriveBits(
    { name: 'ECDH', public: bob.publicKey },
    alice.privateKey,
    256,
  );
  const bobSecret = await subtle.deriveBits(
    { name: 'ECDH', public: alice.publicKey },
    bob.privateKey,
    256,
  );
  assert.deepEqual(Buffer.from(aliceSecret), Buffer.from(bobSecret));
});

test('AES-KW wrapKey 加密导出的密钥材料，unwrapKey 同时重新限制用途', async () => {
  const target = await subtle.generateKey(
    { name: 'HMAC', hash: 'SHA-256', length: 256 },
    true,
    ['sign', 'verify'],
  );
  const wrappingKey = await subtle.generateKey(
    { name: 'AES-KW', length: 256 },
    false,
    ['wrapKey', 'unwrapKey'],
  );
  const wrapped = await subtle.wrapKey('raw', target, wrappingKey, 'AES-KW');
  const unwrapped = await subtle.unwrapKey(
    'raw',
    wrapped,
    wrappingKey,
    'AES-KW',
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify'],
  );
  assert.equal(wrapped.byteLength, 40);
  assert.equal(unwrapped.extractable, false);
  assert.deepEqual(unwrapped.usages, ['verify']);

  const data = encoder.encode('wrapped-key message');
  const signature = await subtle.sign('HMAC', target, data);
  assert.equal(await subtle.verify('HMAC', unwrapped, signature, data), true);
});
