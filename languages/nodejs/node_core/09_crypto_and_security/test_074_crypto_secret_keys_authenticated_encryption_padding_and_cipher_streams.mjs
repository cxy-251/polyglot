// polyglot-covers:
// - nodejs.core.crypto-create-secret-key-properties-export-and-equality
// - nodejs.core.crypto-generate-key-sync-and-callback
// - nodejs.core.crypto-aes-gcm-update-final-aad-and-auth-tag
// - nodejs.core.crypto-aead-authentication-failure-on-tampering
// - nodejs.core.crypto-aes-gcm-auth-tag-length
// - nodejs.core.crypto-cipher-input-and-output-encodings
// - nodejs.core.crypto-cbc-automatic-padding-and-disabled-padding
// - nodejs.core.crypto-cipher-and-decipher-transform-streams
// - nodejs.core.crypto-cipher-key-and-iv-length-validation

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createCipheriv,
  createDecipheriv,
  createSecretKey,
  generateKey,
  generateKeySync,
  getCipherInfo,
} from 'node:crypto';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

function generateKeyAsync(type, options) {
  return new Promise((resolve, reject) => {
    generateKey(type, options, (error, key) => {
      if (error) reject(error);
      else resolve(key);
    });
  });
}

function encryptGcm(plaintext, key, iv, associatedData) {
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(associatedData);
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  return { ciphertext, tag: cipher.getAuthTag() };
}

function decryptGcm(ciphertext, key, iv, associatedData, tag) {
  const decipher = createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAAD(associatedData);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
}

test('SecretKey KeyObject 不暴露可变视图，并记录类型、字节数和相等关系', () => {
  const source = Buffer.alloc(32, 0x11);
  const key = createSecretKey(source);
  source.fill(0xff);

  assert.equal(key.type, 'secret');
  assert.equal(key.symmetricKeySize, 32);
  assert.deepEqual(key.export(), Buffer.alloc(32, 0x11));
  assert.equal(key.equals(createSecretKey(Buffer.alloc(32, 0x11))), true);
  assert.equal(key.equals(createSecretKey(Buffer.alloc(32, 0x12))), false);
  const exported = key.export();
  exported.fill(0);
  assert.deepEqual(key.export(), Buffer.alloc(32, 0x11));
  // 导入与导出都会复制密钥字节；KeyObject 便于表达用途，但应用仍要控制导出与日志边界。
});

test('generateKey 同步与 callback 形式都按 bit 长度创建 SecretKey', async () => {
  const syncKey = generateKeySync('aes', { length: 256 });
  const asyncKey = await generateKeyAsync('hmac', { length: 256 });
  assert.equal(syncKey.type, 'secret');
  assert.equal(syncKey.symmetricKeySize, 32);
  assert.equal(asyncKey.type, 'secret');
  assert.equal(asyncKey.symmetricKeySize, 32);

  assert.throws(
    () => generateKeySync('aes', { length: 200 }),
    (error) => error.code === 'ERR_INVALID_ARG_VALUE',
  );
  // generateKey 的 length 使用 bit；symmetricKeySize 和 Buffer.length 使用 byte，不能混淆。
});

test('AES-GCM 把密文、AAD 与 auth tag 一起认证并正确还原明文', () => {
  const key = createSecretKey(Buffer.alloc(32, 0x21));
  const iv = Buffer.from('00112233445566778899aabb', 'hex');
  const aad = Buffer.from('header:v1');
  const plaintext = Buffer.from('需要保密且验证完整性的内容');
  const { ciphertext, tag } = encryptGcm(plaintext, key, iv, aad);

  assert.notDeepEqual(ciphertext, plaintext);
  assert.equal(tag.length, 16);
  assert.deepEqual(decryptGcm(ciphertext, key, iv, aad, tag), plaintext);
  // GCM 的 IV 必须对同一密钥保持唯一；测试使用固定值只为可重复，生产代码应安全生成并保存它。
});

test('GCM 中密文、AAD 或 auth tag 任一被改动，final 都拒绝输出可信明文', () => {
  const key = Buffer.alloc(32, 0x31);
  const iv = Buffer.alloc(12, 0x41);
  const aad = Buffer.from('metadata');
  const { ciphertext, tag } = encryptGcm(Buffer.from('payload'), key, iv, aad);
  const tamperedCiphertext = Buffer.from(ciphertext);
  tamperedCiphertext[0] ^= 1;
  const tamperedTag = Buffer.from(tag);
  tamperedTag[0] ^= 1;

  for (const attempt of [
    () => decryptGcm(tamperedCiphertext, key, iv, aad, tag),
    () => decryptGcm(ciphertext, key, iv, Buffer.from('other metadata'), tag),
    () => decryptGcm(ciphertext, key, iv, aad, tamperedTag),
  ]) {
    assert.throws(attempt, /authenticate data|bad decrypt/i);
  }
  // decipher.update 可能先返回字节，只有 final 成功后整段明文才经过认证，不能提前使用。
});

test('authTagLength 允许显式采用截断 GCM tag，解密端必须采用相同长度', () => {
  const key = Buffer.alloc(16, 0x51);
  const iv = Buffer.alloc(12, 0x61);
  const cipher = createCipheriv('aes-128-gcm', key, iv, { authTagLength: 12 });
  const ciphertext = Buffer.concat([cipher.update('payload'), cipher.final()]);
  const tag = cipher.getAuthTag();
  assert.equal(tag.length, 12);

  const decipher = createDecipheriv('aes-128-gcm', key, iv, { authTagLength: 12 });
  decipher.setAuthTag(tag);
  assert.equal(
    Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString(),
    'payload',
  );
});

test('update/final 可选择字符串编码，但 Buffer 边界通常更不易混淆', () => {
  const key = Buffer.alloc(32, 0x71);
  const iv = Buffer.alloc(16, 0x81);
  const cipher = createCipheriv('aes-256-cbc', key, iv);
  const encryptedHex = cipher.update('中文 plaintext', 'utf8', 'hex') + cipher.final('hex');
  assert.match(encryptedHex, /^[0-9a-f]+$/);

  const decipher = createDecipheriv('aes-256-cbc', key, iv);
  const decoded = decipher.update(encryptedHex, 'hex', 'utf8') + decipher.final('utf8');
  assert.equal(decoded, '中文 plaintext');
});

test('CBC 默认使用 PKCS#7 padding，关闭后输入必须对齐 block size', () => {
  const key = Buffer.alloc(16, 0x91);
  const iv = Buffer.alloc(16, 0xa1);
  const paddedCipher = createCipheriv('aes-128-cbc', key, iv);
  const padded = Buffer.concat([paddedCipher.update(Buffer.alloc(16)), paddedCipher.final()]);
  assert.equal(padded.length, 32);

  const unpaddedCipher = createCipheriv('aes-128-cbc', key, iv);
  unpaddedCipher.setAutoPadding(false);
  const unpadded = Buffer.concat([
    unpaddedCipher.update(Buffer.alloc(16)),
    unpaddedCipher.final(),
  ]);
  assert.equal(unpadded.length, 16);

  const misaligned = createCipheriv('aes-128-cbc', key, iv).setAutoPadding(false);
  misaligned.update(Buffer.alloc(15));
  assert.throws(() => misaligned.final(), /wrong final block length/i);
});

test('Cipheriv/Decipheriv 是 Transform，可用 pipeline 加密再解密分块输入', async () => {
  const key = Buffer.alloc(32, 0xb1);
  const iv = Buffer.alloc(16, 0xc1);
  const cipher = createCipheriv('aes-256-ctr', key, iv);
  const decipher = createDecipheriv('aes-256-ctr', key, iv);
  const output = [];
  const sink = async function* (source) {
    for await (const chunk of source) output.push(chunk);
  };

  await pipeline(Readable.from(['stream ', 'cipher ', 'workflow']), cipher, decipher, sink);
  assert.equal(Buffer.concat(output).toString(), 'stream cipher workflow');
});

test('算法元数据帮助在创建 Cipher 前校验 key/IV 长度', () => {
  const info = getCipherInfo('aes-256-cbc');
  assert.equal(info.keyLength, 32);
  assert.equal(info.ivLength, 16);
  assert.equal(info.blockSize, 16);

  assert.throws(
    () => createCipheriv('aes-256-cbc', Buffer.alloc(16), Buffer.alloc(16)),
    (error) => error.code === 'ERR_CRYPTO_INVALID_KEYLEN',
  );
  assert.throws(
    () => createCipheriv('aes-256-cbc', Buffer.alloc(32), Buffer.alloc(12)),
    (error) => error.code === 'ERR_CRYPTO_INVALID_IV',
  );
});
