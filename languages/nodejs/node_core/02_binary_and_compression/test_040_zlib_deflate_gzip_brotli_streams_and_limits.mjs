// polyglot-covers:
// - nodejs.core.zlib-deflate-inflate-and-raw
// - nodejs.core.zlib-gzip-gunzip-and-unzip
// - nodejs.core.zlib-brotli-compress-decompress
// - nodejs.core.zlib-callback-and-promisified-apis
// - nodejs.core.zlib-transform-streams-and-pipeline
// - nodejs.core.zlib-dictionaries-and-options
// - nodejs.core.zlib-errors-and-max-output-length

import assert from 'node:assert/strict';
import test from 'node:test';

import { promisify } from 'node:util';
import {
  brotliCompress,
  brotliCompressSync,
  brotliDecompressSync,
  constants,
  createGzip,
  deflateRawSync,
  deflateSync,
  gzip,
  gzipSync,
  gunzipSync,
  inflateRawSync,
  inflateSync,
  unzipSync,
} from 'node:zlib';
import { Readable, Writable } from 'node:stream';
import { pipeline } from 'node:stream/promises';

const payload = Buffer.from('polyglot node.js compression '.repeat(100));

test('deflate/inflate 使用 zlib wrapper 并往返字节', () => {
  const compressed = deflateSync(payload);
  const restored = inflateSync(compressed);

  assert.deepEqual(restored, payload);
  assert.ok(compressed.length < payload.length);
  assert.throws(() => inflateRawSync(compressed), (error) => error.code === 'Z_DATA_ERROR');
});

test('raw deflate 省略 zlib header/trailer，必须配对解码', () => {
  const compressed = deflateRawSync(payload);

  assert.deepEqual(inflateRawSync(compressed), payload);
  assert.throws(() => inflateSync(compressed), (error) => error.code === 'Z_DATA_ERROR');
});

test('gzip/gunzip 往返，unzip 自动识别 gzip 或 zlib wrapper', () => {
  const gzipped = gzipSync(payload, { level: 9 });
  const deflated = deflateSync(payload);

  assert.deepEqual(gunzipSync(gzipped), payload);
  assert.deepEqual(unzipSync(gzipped), payload);
  assert.deepEqual(unzipSync(deflated), payload);
  assert.equal(gzipped[0], 0x1f);
  assert.equal(gzipped[1], 0x8b);
});

test('Brotli 参数通过 constants 键配置质量', () => {
  const compressed = brotliCompressSync(payload, {
    params: {
      [constants.BROTLI_PARAM_QUALITY]: 5,
      [constants.BROTLI_PARAM_MODE]: constants.BROTLI_MODE_TEXT,
    },
  });

  assert.deepEqual(brotliDecompressSync(compressed), payload);
  assert.ok(compressed.length < payload.length);
});

test('callback API 可 promisify，并仍返回 Buffer', async () => {
  const gzipAsync = promisify(gzip);
  const brotliAsync = promisify(brotliCompress);

  const gzipped = await gzipAsync(payload);
  const brotli = await brotliAsync(payload);

  assert.equal(Buffer.isBuffer(gzipped), true);
  assert.equal(Buffer.isBuffer(brotli), true);
  assert.deepEqual(gunzipSync(gzipped), payload);
  assert.deepEqual(brotliDecompressSync(brotli), payload);
});

test('zlib transform 可放入 pipeline 并遵守流背压和错误传播', async () => {
  const chunks = [];
  const destination = new Writable({
    write(chunk, encoding, callback) {
      chunks.push(Buffer.from(chunk));
      callback();
    },
  });

  await pipeline(
    Readable.from([payload.subarray(0, 100), payload.subarray(100)]),
    createGzip(),
    destination,
  );

  assert.deepEqual(gunzipSync(Buffer.concat(chunks)), payload);
});

test('dictionary 必须在压缩和解压两侧一致', () => {
  const dictionary = Buffer.from('polyglot node.js compression ');
  const compressed = deflateSync(payload, { dictionary });

  assert.deepEqual(inflateSync(compressed, { dictionary }), payload);
  assert.throws(
    () => inflateSync(compressed),
    (error) => error.code === 'Z_NEED_DICT',
  );
  assert.throws(
    () => inflateSync(compressed, { dictionary: Buffer.from('wrong') }),
    (error) => ['Z_DATA_ERROR', 'Z_NEED_DICT'].includes(error.code),
  );
});

test('损坏或截断数据产生带 zlib code 的错误', () => {
  const compressed = gzipSync(payload);
  const truncated = compressed.subarray(0, compressed.length - 5);

  assert.throws(
    () => gunzipSync(truncated),
    (error) => typeof error.code === 'string' && error.code.startsWith('Z_'),
  );
  assert.throws(
    () => brotliDecompressSync(Buffer.from('not brotli')),
    (error) => error instanceof Error && /Decompression failed/.test(error.message),
  );
});

test('maxOutputLength 限制解压结果，避免小输入无限占用内存', () => {
  const compressed = gzipSync(payload);

  assert.throws(
    () => gunzipSync(compressed, { maxOutputLength: 100 }),
    (error) => error.code === 'ERR_BUFFER_TOO_LARGE',
  );
  assert.deepEqual(
    gunzipSync(compressed, { maxOutputLength: payload.length }),
    payload,
  );
});
