// polyglot-covers:
// - nodejs.core.crypto-pbkdf2-sync-known-vector-and-validation
// - nodejs.core.crypto-pbkdf2-callback-and-threadpool-asynchrony
// - nodejs.core.crypto-password-string-unicode-normalization-trap
// - nodejs.core.crypto-scrypt-sync-callback-cost-and-memory-limit
// - nodejs.core.crypto-hkdf-sync-callback-and-array-buffer-result
// - nodejs.core.crypto-hkdf-input-keying-material-salt-and-info
// - nodejs.core.crypto-argon2-sync-callback-parameters-and-salt

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  argon2,
  argon2Sync,
  hkdf,
  hkdfSync,
  pbkdf2,
  pbkdf2Sync,
  scrypt,
  scryptSync,
} from 'node:crypto';

function pbkdf2Async(password, salt, iterations, keyLength, digest) {
  return new Promise((resolve, reject) => {
    pbkdf2(password, salt, iterations, keyLength, digest, (error, key) => {
      if (error) reject(error);
      else resolve(key);
    });
  });
}

function scryptAsync(password, salt, keyLength, options) {
  return new Promise((resolve, reject) => {
    scrypt(password, salt, keyLength, options, (error, key) => {
      if (error) reject(error);
      else resolve(key);
    });
  });
}

function hkdfAsync(digest, inputKey, salt, info, keyLength) {
  return new Promise((resolve, reject) => {
    hkdf(digest, inputKey, salt, info, keyLength, (error, key) => {
      if (error) reject(error);
      else resolve(key);
    });
  });
}

function argon2Async(algorithm, parameters) {
  return new Promise((resolve, reject) => {
    argon2(algorithm, parameters, (error, key) => {
      if (error) reject(error);
      else resolve(key);
    });
  });
}

test('PBKDF2 同步形式可用公开向量校验，并要求正迭代次数与显式摘要', () => {
  const key = pbkdf2Sync('password', 'salt', 1, 20, 'sha1');
  assert.equal(key.toString('hex'), '0c60c80f961f0e71f3a9b524af6012062fe037a6');
  assert.throws(
    () => pbkdf2Sync('password', 'salt', 0, 20, 'sha256'),
    (error) => error.code === 'ERR_OUT_OF_RANGE',
  );
  assert.throws(
    () => pbkdf2Sync('password', 'salt', 1, 20),
    (error) => error.code === 'ERR_INVALID_ARG_TYPE',
  );
});

test('PBKDF2 callback 不在调用栈内同步执行，结果与同步形式一致', async () => {
  let sameStack = true;
  const result = new Promise((resolve, reject) => {
    pbkdf2('password', '0123456789abcdef', 100, 32, 'sha256', (error, key) => {
      if (error) reject(error);
      else resolve({ key, sameStack });
    });
  });
  sameStack = false;
  const { key, sameStack: callbackWasSynchronous } = await result;

  assert.equal(callbackWasSynchronous, false);
  assert.deepEqual(
    key,
    pbkdf2Sync('password', '0123456789abcdef', 100, 32, 'sha256'),
  );
  // callback 形式会使用 libuv 线程池；大量并发 KDF 仍会与其他线程池任务竞争容量。
});

test('密码字符串按 UTF-8 字节处理，不会自动做 Unicode 规范化', async () => {
  const composed = 'é';
  const decomposed = 'e\u0301';
  const salt = Buffer.from('sixteen-byte-salt');
  const first = await pbkdf2Async(composed, salt, 10, 16, 'sha256');
  const second = await pbkdf2Async(decomposed, salt, 10, 16, 'sha256');
  const normalized = await pbkdf2Async(decomposed.normalize('NFC'), salt, 10, 16, 'sha256');

  assert.notDeepEqual(first, second);
  assert.deepEqual(first, normalized);
  // 应用若接受人类文本密码，必须自己决定规范化政策并长期保持；运行时不会替你选择。
});

test('scrypt 的同步与异步形式共享参数，cost 必须是大于一的二次幂', async () => {
  const options = {
    cost: 1024,
    blockSize: 8,
    parallelization: 1,
    maxmem: 2 * 1024 * 1024,
  };
  const syncKey = scryptSync('password', '0123456789abcdef', 32, options);
  const asyncKey = await scryptAsync('password', '0123456789abcdef', 32, options);
  assert.deepEqual(asyncKey, syncKey);
  assert.equal(syncKey.length, 32);

  assert.throws(
    () => scryptSync('password', 'salt', 16, { cost: 3 }),
    (error) => error.code === 'ERR_CRYPTO_INVALID_SCRYPT_PARAMS',
  );
});

test('scrypt 的 maxmem 在分配前拒绝过高成本，而不是尝试耗尽内存', () => {
  assert.throws(
    () => scryptSync('password', 'salt', 16, {
      cost: 16_384,
      blockSize: 8,
      parallelization: 1,
      maxmem: 1024,
    }),
    (error) => error.code === 'ERR_CRYPTO_INVALID_SCRYPT_PARAMS',
  );
  // cost、blockSize、parallelization 共同决定资源开销，不能把来自用户的值原样传入。
});

test('HKDF 按 RFC 5869 向量扩展密钥，返回 ArrayBuffer 而不是 Buffer', async () => {
  const inputKey = Buffer.alloc(22, 0x0b);
  const salt = Buffer.from('000102030405060708090a0b0c', 'hex');
  const info = Buffer.from('f0f1f2f3f4f5f6f7f8f9', 'hex');
  const expected = (
    '3cb25f25faacd57a90434f64d0362f2a'
    + '2d2d0a90cf1a5a4c5db02d56ecc4c5bf'
    + '34007208d5b887185865'
  );
  const syncKey = hkdfSync('sha256', inputKey, salt, info, 42);
  const asyncKey = await hkdfAsync('sha256', inputKey, salt, info, 42);

  assert.ok(syncKey instanceof ArrayBuffer);
  assert.ok(asyncKey instanceof ArrayBuffer);
  assert.equal(Buffer.from(syncKey).toString('hex'), expected);
  assert.deepEqual(Buffer.from(asyncKey), Buffer.from(syncKey));
});

test('HKDF 的 salt 与 info 承担不同域分离角色，改变任意一项都会改变输出', () => {
  const derive = (salt, info) => Buffer.from(hkdfSync('sha256', 'input key', salt, info, 32));
  const base = derive('salt-a', 'context-a');
  assert.notDeepEqual(base, derive('salt-b', 'context-a'));
  assert.notDeepEqual(base, derive('salt-a', 'context-b'));
  assert.throws(
    () => hkdfSync('sha256', 'key', 'salt', Buffer.alloc(1025), 32),
    (error) => error.code === 'ERR_OUT_OF_RANGE',
  );
});

test('Argon2id 的参数显式表达内存、轮次和并行度，同输入得到相同 tag', async () => {
  const parameters = {
    message: 'password',
    nonce: Buffer.from('0123456789abcdef'),
    parallelism: 1,
    tagLength: 24,
    memory: 32,
    passes: 2,
    secret: 'server-side pepper',
    associatedData: 'account-v1',
  };
  const syncKey = argon2Sync('argon2id', parameters);
  const asyncKey = await argon2Async('argon2id', parameters);
  assert.ok(Buffer.isBuffer(syncKey));
  assert.deepEqual(asyncKey, syncKey);
  assert.equal(syncKey.length, 24);

  const changedSalt = argon2Sync('argon2id', {
    ...parameters,
    nonce: Buffer.from('fedcba9876543210'),
  });
  assert.notDeepEqual(changedSalt, syncKey);
  // Argon2 在 Node 24.18 仍是 release candidate；参数格式和稳定级别升级时应重新核对。
});

test('Argon2 在执行昂贵工作前校验 nonce 和内存下限', () => {
  const base = {
    message: 'password',
    nonce: Buffer.alloc(16),
    parallelism: 2,
    tagLength: 16,
    memory: 16,
    passes: 1,
  };
  assert.throws(
    () => argon2Sync('argon2id', { ...base, nonce: Buffer.alloc(7) }),
    (error) => error.code === 'ERR_OUT_OF_RANGE',
  );
  assert.throws(
    () => argon2Sync('argon2id', { ...base, memory: 8 }),
    (error) => error.code === 'ERR_OUT_OF_RANGE',
  );
});
