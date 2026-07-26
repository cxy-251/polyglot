// polyglot-covers:
// - nodejs.core.crypto-predefined-diffie-hellman-group-and-shared-secret
// - nodejs.core.crypto-diffie-hellman-group-parameters-and-verify-error
// - nodejs.core.crypto-ecdh-key-formats-convert-key-and-shared-secret
// - nodejs.core.crypto-ecdh-invalid-public-key
// - nodejs.core.crypto-diffie-hellman-key-object-sync-and-callback
// - nodejs.core.crypto-x25519-key-agreement
// - nodejs.core.crypto-ml-kem-generate-encapsulate-and-decapsulate
// - nodejs.core.crypto-kem-sync-and-callback-forms
// - nodejs.core.crypto-ml-kem-implicit-rejection-on-tampered-ciphertext
// - nodejs.core.crypto-ml-kem-raw-seed-and-jwk-round-trip

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ECDH,
  createECDH,
  createPrivateKey,
  createPublicKey,
  decapsulate,
  diffieHellman,
  encapsulate,
  generateKeyPairSync,
  getDiffieHellman,
} from 'node:crypto';

function diffieHellmanAsync(options) {
  return new Promise((resolve, reject) => {
    diffieHellman(options, (error, secret) => {
      if (error) reject(error);
      else resolve(secret);
    });
  });
}

function encapsulateAsync(publicKey) {
  return new Promise((resolve, reject) => {
    encapsulate(publicKey, (error, result) => {
      if (error) reject(error);
      else resolve(result);
    });
  });
}

function decapsulateAsync(privateKey, ciphertext) {
  return new Promise((resolve, reject) => {
    decapsulate(privateKey, ciphertext, (error, sharedKey) => {
      if (error) reject(error);
      else resolve(sharedKey);
    });
  });
}

test('预定义 DH group 省去生成参数，两方用各自私钥计算同一共享秘密', () => {
  const alice = getDiffieHellman('modp14');
  const bob = getDiffieHellman('modp14');
  const alicePublic = alice.generateKeys();
  const bobPublic = bob.generateKeys();
  const aliceSecret = alice.computeSecret(bobPublic);
  const bobSecret = bob.computeSecret(alicePublic);

  assert.deepEqual(aliceSecret, bobSecret);
  assert.equal(aliceSecret.length, 256);
  assert.deepEqual(alice.getPrime(), bob.getPrime());
  assert.deepEqual(alice.getGenerator(), bob.getGenerator());
  assert.equal(alice.verifyError, 0);
  // 共享秘密还不是应用密钥；通常应再经过 HKDF，并把双方身份和协议上下文放入 info。
});

test('ECDH 支持压缩/未压缩公钥格式，convertKey 只改变编码不改变点', () => {
  const alice = createECDH('prime256v1');
  const bob = createECDH('prime256v1');
  const aliceCompressed = alice.generateKeys(undefined, 'compressed');
  const bobUncompressed = bob.generateKeys(undefined, 'uncompressed');
  const converted = ECDH.convertKey(
    aliceCompressed,
    'prime256v1',
    undefined,
    undefined,
    'uncompressed',
  );

  assert.equal(aliceCompressed.length, 33);
  assert.equal(converted.length, 65);
  assert.deepEqual(converted, alice.getPublicKey(undefined, 'uncompressed'));
  assert.deepEqual(alice.computeSecret(bobUncompressed), bob.computeSecret(aliceCompressed));
});

test('ECDH 拒绝不在曲线上的对端公钥，而不是产出可疑共享秘密', () => {
  const alice = createECDH('prime256v1');
  alice.generateKeys();
  assert.throws(
    () => alice.computeSecret(Buffer.alloc(65)),
    (error) => error.code === 'ERR_CRYPTO_ECDH_INVALID_PUBLIC_KEY',
  );
});

test('KeyObject diffieHellman 支持 X25519，同步和 callback 得到相同 32 字节秘密', async () => {
  const alice = generateKeyPairSync('x25519');
  const bob = generateKeyPairSync('x25519');
  const aliceSecret = diffieHellman({
    privateKey: alice.privateKey,
    publicKey: bob.publicKey,
  });
  const bobSecret = await diffieHellmanAsync({
    privateKey: bob.privateKey,
    publicKey: alice.publicKey,
  });

  assert.equal(alice.publicKey.asymmetricKeyType, 'x25519');
  assert.equal(aliceSecret.length, 32);
  assert.deepEqual(aliceSecret, bobSecret);
  // X25519 只协商秘密，不认证对端；缺少签名或可信公钥绑定时仍会遭遇中间人攻击。
});

test('diffieHellman 要求兼容的公私钥类型', () => {
  const x25519 = generateKeyPairSync('x25519');
  const ec = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  assert.throws(
    () => diffieHellman({ privateKey: x25519.privateKey, publicKey: ec.publicKey }),
    (error) => error.code === 'ERR_CRYPTO_INCOMPATIBLE_KEY',
  );
});

test('ML-KEM encapsulate 用公钥产生密文和共享密钥，私钥 decapsulate 恢复密钥', () => {
  const { publicKey, privateKey } = generateKeyPairSync('ml-kem-512');
  const { sharedKey, ciphertext } = encapsulate(publicKey);
  const recovered = decapsulate(privateKey, ciphertext);

  assert.equal(publicKey.asymmetricKeyType, 'ml-kem-512');
  assert.equal(privateKey.asymmetricKeyType, 'ml-kem-512');
  assert.equal(sharedKey.length, 32);
  assert.equal(ciphertext.length, 768);
  assert.deepEqual(recovered, sharedKey);
  // encapsulate 每次都会产生新密钥与密文；KEM 用来封装会话密钥，不直接加密业务正文。
});

test('ML-KEM callback 形式把较重计算放入线程池', async () => {
  const { publicKey, privateKey } = generateKeyPairSync('ml-kem-512');
  const { sharedKey, ciphertext } = await encapsulateAsync(publicKey);
  const recovered = await decapsulateAsync(privateKey, ciphertext);
  assert.deepEqual(recovered, sharedKey);
});

test('ML-KEM 对正确长度但被篡改的密文执行 implicit rejection', () => {
  const { publicKey, privateKey } = generateKeyPairSync('ml-kem-512');
  const { sharedKey, ciphertext } = encapsulate(publicKey);
  const tampered = Buffer.from(ciphertext);
  tampered[0] ^= 1;
  const rejectedSecret = decapsulate(privateKey, tampered);

  assert.equal(rejectedSecret.length, sharedKey.length);
  assert.notDeepEqual(rejectedSecret, sharedKey);
  // ML-KEM 的隐式拒绝返回不可预测替代秘密而非认证错误；后续 AEAD 验证才会暴露封装无效。
});

test('Node 24.18 可用 raw seed 与 JWK 往返 ML-KEM 私钥', () => {
  const generated = generateKeyPairSync('ml-kem-512');
  const seed = generated.privateKey.export({ format: 'raw-seed' });
  const fromSeed = createPrivateKey({
    key: seed,
    format: 'raw-seed',
    asymmetricKeyType: 'ml-kem-512',
  });
  assert.equal(seed.length, 64);
  assert.equal(fromSeed.equals(generated.privateKey), true);
  assert.equal(createPublicKey(fromSeed).equals(generated.publicKey), true);

  const jwk = generated.privateKey.export({ format: 'jwk' });
  assert.equal(jwk.kty, 'AKP');
  assert.equal(jwk.alg, 'ML-KEM-512');
  assert.equal(typeof jwk.priv, 'string');
  assert.equal(typeof jwk.pub, 'string');
  const fromJwk = createPrivateKey({ key: jwk, format: 'jwk' });
  assert.equal(fromJwk.equals(generated.privateKey), true);
});
