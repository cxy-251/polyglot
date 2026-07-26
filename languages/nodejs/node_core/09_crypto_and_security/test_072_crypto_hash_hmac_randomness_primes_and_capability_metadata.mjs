// polyglot-covers:
// - nodejs.core.crypto-create-hash-update-copy-digest-and-finalization
// - nodejs.core.crypto-one-shot-hash-and-xof-output-length
// - nodejs.core.crypto-hash-stream
// - nodejs.core.crypto-hmac
// - nodejs.core.crypto-timing-safe-equal
// - nodejs.core.crypto-random-bytes-sync-and-callback
// - nodejs.core.crypto-random-fill-sync-and-callback
// - nodejs.core.crypto-random-int-exclusive-upper-bound
// - nodejs.core.crypto-random-uuid-v4-and-v7
// - nodejs.core.crypto-get-random-values
// - nodejs.core.crypto-generate-and-check-prime
// - nodejs.core.crypto-algorithm-capability-metadata
// - nodejs.core.crypto-fips-and-secure-heap-state

import assert from 'node:assert/strict';
import test from 'node:test';

import { Readable } from 'node:stream';
import {
  checkPrime,
  checkPrimeSync,
  createHash,
  createHmac,
  generatePrime,
  generatePrimeSync,
  getCipherInfo,
  getCiphers,
  getCurves,
  getFips,
  getHashes,
  getRandomValues,
  hash,
  randomBytes,
  randomFill,
  randomFillSync,
  randomInt,
  randomUUID,
  randomUUIDv7,
  secureHeapUsed,
  timingSafeEqual,
} from 'node:crypto';

function randomBytesAsync(size) {
  return new Promise((resolve, reject) => {
    randomBytes(size, (error, buffer) => {
      if (error) reject(error);
      else resolve(buffer);
    });
  });
}

function randomFillAsync(buffer, offset, size) {
  return new Promise((resolve, reject) => {
    randomFill(buffer, offset, size, (error, filled) => {
      if (error) reject(error);
      else resolve(filled);
    });
  });
}

function randomIntAsync(min, max) {
  return new Promise((resolve, reject) => {
    randomInt(min, max, (error, value) => {
      if (error) reject(error);
      else resolve(value);
    });
  });
}

function generatePrimeAsync(size, options) {
  return new Promise((resolve, reject) => {
    generatePrime(size, options, (error, prime) => {
      if (error) reject(error);
      else resolve(prime);
    });
  });
}

function checkPrimeAsync(candidate) {
  return new Promise((resolve, reject) => {
    checkPrime(candidate, (error, result) => {
      if (error) reject(error);
      else resolve(result);
    });
  });
}

test('Hash 支持增量输入和分支 copy，digest 后实例不可复用', () => {
  const common = createHash('sha256').update('poly');
  const first = common.copy().update('glot').digest('hex');
  const second = common.copy().update('graph').digest('hex');
  const commonDigest = common.digest('hex');

  assert.equal(first, hash('sha256', 'polyglot'));
  assert.equal(second, hash('sha256', 'polygraph'));
  assert.equal(commonDigest, hash('sha256', 'poly'));
  assert.throws(
    () => common.update('late data'),
    (error) => error.code === 'ERR_CRYPTO_HASH_FINALIZED',
  );
  // copy 复制的是当前摘要状态，适合共享大前缀；它不是 digest 后复活原 Hash 的手段。
});

test('one-shot hash 默认返回 hex，也可返回 Buffer 并设置 XOF 长度', () => {
  assert.equal(
    hash('sha256', 'abc'),
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
  );
  const bytes = hash('sha256', Buffer.from('abc'), 'buffer');
  assert.ok(Buffer.isBuffer(bytes));
  assert.equal(bytes.length, 32);

  const shake = hash('shake256', 'abc', { outputEncoding: 'buffer', outputLength: 20 });
  assert.ok(Buffer.isBuffer(shake));
  assert.equal(shake.length, 20);
  // 小型、已在内存中的输入适合 one-shot hash；大数据应继续采用增量或流式 Hash。
});

test('Hash 本身是 Transform，流结束后只产出一个摘要块', async () => {
  const digestStream = createHash('sha256');
  Readable.from(['poly', 'glot']).pipe(digestStream);
  const chunks = [];
  for await (const chunk of digestStream) chunks.push(chunk);

  assert.equal(chunks.length, 1);
  assert.equal(Buffer.concat(chunks).toString('hex'), hash('sha256', 'polyglot'));
});

test('HMAC 同时依赖消息与密钥，普通 Hash 不能替代消息认证码', () => {
  const first = createHmac('sha256', 'secret').update('message').digest('hex');
  const otherKey = createHmac('sha256', 'other').update('message').digest('hex');
  const otherMessage = createHmac('sha256', 'secret').update('changed').digest('hex');

  assert.equal(first.length, 64);
  assert.notEqual(first, otherKey);
  assert.notEqual(first, otherMessage);
  assert.notEqual(first, hash('sha256', 'secretmessage'));
});

test('timingSafeEqual 要求等长字节，但外围流程也必须避免泄漏时序', () => {
  const actual = createHmac('sha256', 'key').update('payload').digest();
  const expected = Buffer.from(actual);
  const changed = Buffer.from(actual);
  changed[0] ^= 0xff;

  assert.equal(timingSafeEqual(actual, expected), true);
  assert.equal(timingSafeEqual(actual, changed), false);
  assert.throws(
    () => timingSafeEqual(actual, Buffer.alloc(1)),
    (error) => error.code === 'ERR_CRYPTO_TIMING_SAFE_EQUAL_LENGTH',
  );
  // 该函数只让比较本身尽量恒定时间；长度检查、解析和错误响应仍可能暴露外围时序。
});

test('randomBytes 的同步与 callback 形式都返回指定长度的 Buffer', async () => {
  const syncValue = randomBytes(24);
  const asyncValue = await randomBytesAsync(24);
  assert.ok(Buffer.isBuffer(syncValue));
  assert.ok(Buffer.isBuffer(asyncValue));
  assert.equal(syncValue.length, 24);
  assert.equal(asyncValue.length, 24);
});

test('randomFill 就地填充指定字节范围，并返回同一个视图', async () => {
  const syncBuffer = Buffer.alloc(12, 0);
  assert.equal(randomFillSync(syncBuffer, 3, 6), syncBuffer);
  assert.deepEqual([...syncBuffer.subarray(0, 3)], [0, 0, 0]);
  assert.deepEqual([...syncBuffer.subarray(9)], [0, 0, 0]);

  const asyncBuffer = new Uint8Array(10);
  const returned = await randomFillAsync(asyncBuffer, 2, 5);
  assert.equal(returned, asyncBuffer);
  assert.deepEqual([...asyncBuffer.subarray(0, 2)], [0, 0]);
  assert.deepEqual([...asyncBuffer.subarray(7)], [0, 0, 0]);
  // 随机字节有可能恰好为零，所以测试范围边界，而不以“至少一个非零”判断随机性。
});

test('randomInt 采用 [min, max) 区间，范围必须小于 2^48', async () => {
  const syncValue = randomInt(10, 11);
  const asyncValue = await randomIntAsync(-3, -2);
  assert.equal(syncValue, 10);
  assert.equal(asyncValue, -3);
  assert.throws(
    () => randomInt(0, 2 ** 48 + 1),
    (error) => error.code === 'ERR_OUT_OF_RANGE',
  );
});

test('randomUUID 生成 v4，randomUUIDv7 在高位嵌入毫秒时间戳', () => {
  const version4 = randomUUID({ disableEntropyCache: true });
  const version7 = randomUUIDv7({ disableEntropyCache: true });
  assert.match(version4, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-/);
  assert.match(version7, /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-/);
  assert.equal(version4.length, 36);
  assert.equal(version7.length, 36);
  // v7 适合按时间大致排序，但官方明确说明系统时钟非单调，不能要求连续调用严格递增。
});

test('getRandomValues 原地填充整数视图，并保留 Web Crypto 的 65536 字节上限', () => {
  const values = new Uint32Array(4);
  assert.equal(getRandomValues(values), values);
  assert.throws(
    () => getRandomValues(new Uint8Array(65_537)),
    (error) => error.name === 'QuotaExceededError',
  );
});

test('generatePrime/checkPrime 提供同步与异步形式，bigint 避免手动解码', async () => {
  const syncPrime = generatePrimeSync(32, { bigint: true });
  const asyncPrime = await generatePrimeAsync(32, { bigint: true });
  assert.equal(typeof syncPrime, 'bigint');
  assert.equal(typeof asyncPrime, 'bigint');
  assert.equal(checkPrimeSync(syncPrime), true);
  assert.equal(await checkPrimeAsync(asyncPrime), true);
  assert.equal(checkPrimeSync(21n), false);
  // 素数尺寸会直接影响计算时长；普通请求路径不应同步生成大素数。
});

test('能力查询反映锁定 OpenSSL 构建，不应硬编码完整算法清单', () => {
  assert.ok(getHashes().includes('sha256'));
  assert.ok(getCiphers().includes('aes-256-gcm'));
  assert.ok(getCurves().includes('prime256v1'));
  assert.deepEqual(
    getCipherInfo('aes-256-gcm'),
    {
      mode: 'gcm',
      name: 'id-aes256-gcm',
      nid: 901,
      blockSize: 1,
      ivLength: 12,
      keyLength: 32,
    },
  );
  assert.equal(getCipherInfo('not-a-real-cipher'), undefined);
});

test('FIPS 与 secure heap 是进程启动状态，本测试只读取而不全局改写', () => {
  assert.ok(getFips() === 0 || getFips() === 1);
  const heap = secureHeapUsed();
  assert.equal(typeof heap.total, 'number');
  assert.equal(typeof heap.used, 'number');
  assert.equal(typeof heap.utilization, 'number');
  assert.equal(typeof heap.min, 'number');
  assert.ok(heap.used <= heap.total);
});
