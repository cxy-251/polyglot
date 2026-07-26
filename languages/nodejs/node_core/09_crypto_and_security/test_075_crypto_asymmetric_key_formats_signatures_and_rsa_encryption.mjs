// polyglot-covers:
// - nodejs.core.crypto-generate-key-pair-sync-and-callback
// - nodejs.core.crypto-asymmetric-key-object-type-details-and-equality
// - nodejs.core.crypto-private-key-encrypted-pkcs8-pem-export-import
// - nodejs.core.crypto-public-key-spki-der-and-jwk-export-import
// - nodejs.core.crypto-create-public-key-from-private-key
// - nodejs.core.crypto-sign-verify-one-shot-and-rsa-pss-options
// - nodejs.core.crypto-sign-and-verify-streaming-objects
// - nodejs.core.crypto-ed25519-signature-with-null-algorithm
// - nodejs.core.crypto-rsa-oaep-public-encrypt-private-decrypt
// - nodejs.core.crypto-rsa-oaep-label-and-tamper-failure
// - nodejs.core.crypto-private-encrypt-public-decrypt-legacy-operation

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  constants,
  createPrivateKey,
  createPublicKey,
  createSign,
  createVerify,
  generateKeyPair,
  generateKeyPairSync,
  privateDecrypt,
  privateEncrypt,
  publicDecrypt,
  publicEncrypt,
  sign,
  verify,
} from 'node:crypto';

function generateKeyPairAsync(type, options = {}) {
  return new Promise((resolve, reject) => {
    generateKeyPair(type, options, (error, publicKey, privateKey) => {
      if (error) reject(error);
      else resolve({ publicKey, privateKey });
    });
  });
}

function createRsaPair() {
  return generateKeyPairSync('rsa', {
    modulusLength: 1024,
    publicExponent: 0x10001,
  });
}

test('RSA KeyObject 区分 public/private 类型并暴露非敏感算法详情', () => {
  const { publicKey, privateKey } = createRsaPair();
  assert.equal(publicKey.type, 'public');
  assert.equal(privateKey.type, 'private');
  assert.equal(publicKey.asymmetricKeyType, 'rsa');
  assert.equal(privateKey.asymmetricKeyType, 'rsa');
  assert.deepEqual(publicKey.asymmetricKeyDetails, {
    modulusLength: 1024,
    publicExponent: 65_537n,
  });
  assert.equal(publicKey.equals(createPublicKey(privateKey)), true);
  assert.equal(publicKey.equals(privateKey), false);
});

test('私钥可加密导出为 PKCS#8 PEM，导入需要匹配的 passphrase', () => {
  const { privateKey } = createRsaPair();
  const pem = privateKey.export({
    type: 'pkcs8',
    format: 'pem',
    cipher: 'aes-256-cbc',
    passphrase: 'correct horse battery staple',
  });
  assert.equal(typeof pem, 'string');
  assert.match(pem, /BEGIN ENCRYPTED PRIVATE KEY/);

  const imported = createPrivateKey({
    key: pem,
    format: 'pem',
    passphrase: 'correct horse battery staple',
  });
  assert.equal(imported.equals(privateKey), true);
  assert.throws(
    () => createPrivateKey({ key: pem, passphrase: 'wrong passphrase' }),
    /bad decrypt|pkcs12 cipherfinal error|maybe wrong password/i,
  );
});

test('公钥可在 SPKI DER 与 JWK 之间导出导入，不包含私有参数', () => {
  const { publicKey } = createRsaPair();
  const der = publicKey.export({ type: 'spki', format: 'der' });
  const fromDer = createPublicKey({ key: der, type: 'spki', format: 'der' });
  assert.ok(Buffer.isBuffer(der));
  assert.equal(fromDer.equals(publicKey), true);

  const jwk = publicKey.export({ format: 'jwk' });
  assert.equal(jwk.kty, 'RSA');
  assert.equal(typeof jwk.n, 'string');
  assert.equal(jwk.e, 'AQAB');
  assert.equal('d' in jwk, false);
  assert.equal(createPublicKey({ key: jwk, format: 'jwk' }).equals(publicKey), true);
  // 公钥可公开不等于可随意替换；应用仍需通过证书、指纹或可信配置认证它的来源。
});

test('one-shot sign/verify 支持 RSA-PSS，消息或参数不匹配时返回 false', () => {
  const { publicKey, privateKey } = createRsaPair();
  const data = Buffer.from('signed payload');
  const options = {
    key: privateKey,
    padding: constants.RSA_PKCS1_PSS_PADDING,
    saltLength: constants.RSA_PSS_SALTLEN_DIGEST,
  };
  const signature = sign('sha256', data, options);

  assert.equal(verify('sha256', data, {
    key: publicKey,
    padding: constants.RSA_PKCS1_PSS_PADDING,
    saltLength: constants.RSA_PSS_SALTLEN_DIGEST,
  }, signature), true);
  assert.equal(verify('sha256', Buffer.from('changed'), {
    key: publicKey,
    padding: constants.RSA_PKCS1_PSS_PADDING,
    saltLength: constants.RSA_PSS_SALTLEN_DIGEST,
  }, signature), false);
});

test('Sign/Verify 对象支持分块 update，verify 消费签名后不能复用', () => {
  const { publicKey, privateKey } = createRsaPair();
  const signer = createSign('sha256');
  signer.update('first ');
  signer.update('second');
  const signature = signer.sign(privateKey);

  const verifier = createVerify('sha256');
  verifier.update('first ');
  verifier.update('second');
  assert.equal(verifier.verify(publicKey, signature), true);
  assert.throws(
    () => verifier.update('late'),
    (error) => error.code === 'ERR_CRYPTO_INVALID_STATE',
  );
});

test('Ed25519 自带哈希方案，one-shot sign/verify 的 algorithm 必须为 null', async () => {
  const { publicKey, privateKey } = await generateKeyPairAsync('ed25519');
  const data = Buffer.from('ed25519 message');
  const signature = sign(null, data, privateKey);
  assert.equal(signature.length, 64);
  assert.equal(verify(null, data, publicKey, signature), true);
  assert.equal(verify(null, Buffer.from('changed'), publicKey, signature), false);
  assert.equal(publicKey.asymmetricKeyType, 'ed25519');
});

test('RSA-OAEP 用公钥加密、私钥解密，并把 label 纳入操作参数', () => {
  const { publicKey, privateKey } = createRsaPair();
  const plaintext = Buffer.from('short secret');
  const oaepLabel = Buffer.from('protocol:v1');
  const ciphertext = publicEncrypt({
    key: publicKey,
    oaepHash: 'sha256',
    oaepLabel,
  }, plaintext);
  assert.notDeepEqual(ciphertext, plaintext);
  assert.deepEqual(privateDecrypt({
    key: privateKey,
    oaepHash: 'sha256',
    oaepLabel,
  }, ciphertext), plaintext);

  assert.throws(
    () => privateDecrypt({
      key: privateKey,
      oaepHash: 'sha256',
      oaepLabel: Buffer.from('protocol:v2'),
    }, ciphertext),
    /oaep decoding error/i,
  );
});

test('RSA-OAEP 密文被修改时解密失败，且明文长度受 modulus 与 hash 限制', () => {
  const { publicKey, privateKey } = createRsaPair();
  const ciphertext = publicEncrypt({ key: publicKey, oaepHash: 'sha256' }, 'secret');
  ciphertext[0] ^= 1;
  assert.throws(
    () => privateDecrypt({ key: privateKey, oaepHash: 'sha256' }, ciphertext),
    /oaep decoding error|data too large for modulus/i,
  );
  assert.throws(
    () => publicEncrypt({ key: publicKey, oaepHash: 'sha256' }, Buffer.alloc(63)),
    /data too large for key size/i,
  );
  // RSA 不适合直接加密大正文；常见做法是随机生成对称密钥，再用 RSA 封装该短密钥。
});

test('privateEncrypt/publicDecrypt 是旧式私钥运算，不替代现代签名 API', () => {
  const { publicKey, privateKey } = createRsaPair();
  const payload = Buffer.from('legacy recovery payload');
  const transformed = privateEncrypt({
    key: privateKey,
    padding: constants.RSA_PKCS1_PADDING,
  }, payload);
  const recovered = publicDecrypt({
    key: publicKey,
    padding: constants.RSA_PKCS1_PADDING,
  }, transformed);
  assert.deepEqual(recovered, payload);
  // 任何持有公钥的人都能恢复内容，所以这不是加密；新代码应使用 sign/verify 表达签名。
});
