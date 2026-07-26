// polyglot-covers:
// - nodejs.core.webcrypto-subtle-crypto-supports-feature-detection
// - nodejs.core.webcrypto-sha3-digest
// - nodejs.core.webcrypto-aes-ocb-and-chacha20-poly1305
// - nodejs.core.webcrypto-argon2id-import-and-derive-bits
// - nodejs.core.webcrypto-kmac-key-sign-verify-output-length-and-customization
// - nodejs.core.webcrypto-ml-dsa-generate-sign-verify-and-context
// - nodejs.core.webcrypto-ml-kem-encapsulate-and-decapsulate-bits
// - nodejs.core.webcrypto-ml-kem-encapsulate-and-decapsulate-key
// - nodejs.core.webcrypto-modern-algorithms-experimental-warning

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

test('SubtleCrypto.supports 在调用前检查操作、算法和派生目标组合', () => {
  assert.equal(globalThis.SubtleCrypto, subtle.constructor);
  assert.equal(SubtleCrypto.supports('digest', 'SHA3-256'), true);
  assert.equal(
    SubtleCrypto.supports('generateKey', { name: 'AES-OCB', length: 128 }),
    true,
  );
  assert.equal(SubtleCrypto.supports('generateKey', 'AES-OCB'), false);
  assert.equal(SubtleCrypto.supports('generateKey', 'not-an-algorithm'), false);
  assert.equal(
    SubtleCrypto.supports(
      'deriveKey',
      {
        name: 'Argon2id',
        nonce: new Uint8Array(16),
        parallelism: 1,
        memory: 32,
        passes: 1,
      },
      { name: 'AES-GCM', length: 256 },
    ),
    true,
  );
  // supports 属于 active development；它适合能力分支，不表示所选参数满足业务安全要求。
});

test('SHA3-256 digest 使用标准向量，并与 SHA-256 是不同算法', async () => {
  const sha3 = await subtle.digest('SHA3-256', encoder.encode('abc'));
  const sha2 = await subtle.digest('SHA-256', encoder.encode('abc'));
  assert.equal(
    Buffer.from(sha3).toString('hex'),
    '3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532',
  );
  assert.notDeepEqual(Buffer.from(sha3), Buffer.from(sha2));
});

test('AES-OCB 与 ChaCha20-Poly1305 共享 AeadParams 形状和附加 tag 语义', async () => {
  for (const name of ['AES-OCB', 'ChaCha20-Poly1305']) {
    const keyParameters = name === 'AES-OCB' ? { name, length: 128 } : { name };
    const key = await subtle.generateKey(keyParameters, false, ['encrypt', 'decrypt']);
    const algorithm = {
      name,
      iv: new Uint8Array(12),
      additionalData: encoder.encode('metadata'),
      tagLength: 128,
    };
    const plaintext = encoder.encode(`${name} payload`);
    const encrypted = await subtle.encrypt(algorithm, key, plaintext);
    const decrypted = await subtle.decrypt(algorithm, key, encrypted);
    assert.equal(encrypted.byteLength, plaintext.byteLength + 16);
    assert.equal(decoder.decode(decrypted), `${name} payload`);
  }
  // 两者在 Node 24 属于 Modern Algorithms active-development 范围，跨运行时前应先 supports。
});

test('Argon2id 通过 raw-secret 导入密码材料，并由 deriveBits 的 length 决定 tag 大小', async () => {
  const password = await subtle.importKey(
    'raw-secret',
    encoder.encode('password'),
    'Argon2id',
    false,
    ['deriveBits'],
  );
  const parameters = {
    name: 'Argon2id',
    nonce: encoder.encode('0123456789abcdef'),
    parallelism: 1,
    memory: 32,
    passes: 2,
    associatedData: encoder.encode('account:v1'),
    secretValue: encoder.encode('server pepper'),
  };
  const first = await subtle.deriveBits(parameters, password, 192);
  const second = await subtle.deriveBits(parameters, password, 192);
  assert.equal(first.byteLength, 24);
  assert.deepEqual(Buffer.from(first), Buffer.from(second));

  const changed = await subtle.deriveBits(
    { ...parameters, nonce: encoder.encode('fedcba9876543210') },
    password,
    192,
  );
  assert.notDeepEqual(Buffer.from(first), Buffer.from(changed));
});

test('KMAC 把输出长度与 customization 纳入 MAC，verify 返回布尔结果', async () => {
  const key = await subtle.generateKey(
    { name: 'KMAC128', length: 256 },
    false,
    ['sign', 'verify'],
  );
  const algorithm = {
    name: 'KMAC128',
    outputLength: 256,
    customization: encoder.encode('polyglot:v1'),
  };
  const data = encoder.encode('kmac message');
  const signature = await subtle.sign(algorithm, key, data);
  assert.equal(signature.byteLength, 32);
  assert.equal(await subtle.verify(algorithm, key, signature, data), true);
  assert.equal(await subtle.verify(
    { ...algorithm, customization: encoder.encode('polyglot:v2') },
    key,
    signature,
    data,
  ), false);
  // generateKey 的 length 是密钥位数；sign/verify 的 outputLength 是 MAC 位数，二者不能混用。
});

test('ML-DSA-44 使用可选 context 做域分离，context 不匹配时验证失败', async () => {
  const pair = await subtle.generateKey('ML-DSA-44', false, ['sign', 'verify']);
  const data = encoder.encode('post-quantum signature');
  const algorithm = { name: 'ML-DSA-44', context: encoder.encode('protocol:v1') };
  const signature = await subtle.sign(algorithm, pair.privateKey, data);

  assert.equal(pair.publicKey.algorithm.name, 'ML-DSA-44');
  assert.ok(signature.byteLength > 1000);
  assert.equal(await subtle.verify(algorithm, pair.publicKey, signature, data), true);
  assert.equal(await subtle.verify(
    { name: 'ML-DSA-44', context: encoder.encode('protocol:v2') },
    pair.publicKey,
    signature,
    data,
  ), false);
});

test('ML-KEM encapsulateBits/decapsulateBits 交换 ArrayBuffer 共享秘密', async () => {
  const pair = await subtle.generateKey(
    'ML-KEM-512',
    false,
    ['encapsulateBits', 'decapsulateBits'],
  );
  const { sharedKey, ciphertext } = await subtle.encapsulateBits(
    'ML-KEM-512',
    pair.publicKey,
  );
  const recovered = await subtle.decapsulateBits(
    'ML-KEM-512',
    pair.privateKey,
    ciphertext,
  );
  assert.ok(sharedKey instanceof ArrayBuffer);
  assert.ok(ciphertext instanceof ArrayBuffer);
  assert.equal(sharedKey.byteLength, 32);
  assert.equal(ciphertext.byteLength, 768);
  assert.deepEqual(Buffer.from(recovered), Buffer.from(sharedKey));
});

test('encapsulateKey/decapsulateKey 直接得到受 usages 约束的 AES CryptoKey', async () => {
  const pair = await subtle.generateKey(
    'ML-KEM-512',
    false,
    ['encapsulateKey', 'decapsulateKey'],
  );
  const encapsulated = await subtle.encapsulateKey(
    'ML-KEM-512',
    pair.publicKey,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt'],
  );
  const recovered = await subtle.decapsulateKey(
    'ML-KEM-512',
    pair.privateKey,
    encapsulated.ciphertext,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt'],
  );

  assert.equal(encapsulated.sharedKey.algorithm.name, 'AES-GCM');
  assert.deepEqual(
    Buffer.from(await subtle.exportKey('raw', recovered)),
    Buffer.from(await subtle.exportKey('raw', encapsulated.sharedKey)),
  );
  assert.deepEqual(recovered.usages, ['encrypt', 'decrypt']);
});

test('Modern Algorithms 与扩展方法会发 ExperimentalWarning，测试精确捕获后恢复全局函数', () => {
  assert.ok(experimentalWarnings.some((warning) => warning.includes('supports')));
  assert.ok(experimentalWarnings.some((warning) => warning.includes('AES-OCB')));
  assert.ok(experimentalWarnings.some((warning) => warning.includes('encapsulateBits')));
  // 普通应用不应全局吞警告；本文件只在 node:test 的隔离子进程内捕获已知类别并明确断言。
});
