// polyglot-covers:
// - nodejs.core.string-decoder-incomplete-multibyte-sequences
// - nodejs.core.text-decoder-streaming-fatal-and-bom
// - nodejs.core.buffer-transcode
// - nodejs.core.buffer-is-utf8-and-is-ascii
// - nodejs.core.atob-btoa-latin1-contract
// - nodejs.core.blob-bytes-text-slice-and-object-url

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  Blob,
  Buffer,
  atob,
  btoa,
  isAscii,
  isUtf8,
  resolveObjectURL,
  transcode,
} from 'node:buffer';
import { StringDecoder } from 'node:string_decoder';

test('StringDecoder 暂存被 chunk 边界切开的 UTF-8 字符', () => {
  const bytes = Buffer.from('A中💡B');
  const decoder = new StringDecoder('utf8');

  assert.equal(decoder.write(bytes.subarray(0, 2)), 'A');
  assert.equal(decoder.write(bytes.subarray(2, 6)), '中');
  assert.equal(decoder.write(bytes.subarray(6)), '💡B');
  assert.equal(decoder.end(), '');

  // 对每个 chunk 单独 toString 会把不完整序列替换为 U+FFFD，流式解码器才能跨块拼接。
});

test('StringDecoder.end 会用替换字符结束残缺输入', () => {
  const decoder = new StringDecoder('utf8');
  assert.equal(decoder.write(Buffer.from([0xe4, 0xb8])), '');
  assert.equal(decoder.end(), '�');

  const utf16 = new StringDecoder('utf16le');
  assert.equal(utf16.write(Buffer.from([0x41])), '');
  assert.equal(utf16.end(), '');
});

test('TextDecoder 的 stream 选项也能跨调用保留不完整序列', () => {
  const bytes = new TextEncoder().encode('中文');
  const decoder = new TextDecoder('utf-8');

  assert.equal(decoder.decode(bytes.subarray(0, 2), { stream: true }), '');
  assert.equal(decoder.decode(bytes.subarray(2, 4), { stream: true }), '中');
  assert.equal(decoder.decode(bytes.subarray(4), { stream: true }), '文');
  assert.equal(decoder.decode(), '');
});

test('fatal 模式拒绝非法序列，默认模式插入替换字符', () => {
  const invalid = Uint8Array.of(0x61, 0xff, 0x62);

  assert.equal(new TextDecoder().decode(invalid), 'a�b');
  assert.throws(
    () => new TextDecoder('utf-8', { fatal: true }).decode(invalid),
    TypeError,
  );
});

test('ignoreBOM 控制是否把开头 BOM 保留为普通字符', () => {
  const bytes = Uint8Array.of(0xef, 0xbb, 0xbf, 0x41);

  assert.equal(new TextDecoder('utf-8').decode(bytes), 'A');
  assert.equal(new TextDecoder('utf-8', { ignoreBOM: true }).decode(bytes), '\ufeffA');
});

test('transcode 在受支持字符编码之间转换 Buffer', () => {
  const utf8 = Buffer.from('Héllo', 'utf8');
  const latin1 = transcode(utf8, 'utf8', 'latin1');

  assert.equal(latin1.toString('hex'), '48e96c6c6f');
  assert.equal(transcode(latin1, 'latin1', 'utf8').toString(), 'Héllo');

  // 目标编码无法表示字符时会替换而非抛错。
  assert.equal(transcode(Buffer.from('中'), 'utf8', 'ascii').toString('ascii'), '?');
});

test('isUtf8/isAscii 验证字节视图而不执行字符串往返', () => {
  const valid = Buffer.from('中文');
  const invalid = Buffer.from([0xc0, 0xaf]);
  const ascii = Buffer.from('plain ASCII');

  assert.equal(isUtf8(valid), true);
  assert.equal(isUtf8(invalid), false);
  assert.equal(isAscii(ascii), true);
  assert.equal(isAscii(valid), false);
  const exactArrayBuffer = valid.buffer.slice(
    valid.byteOffset,
    valid.byteOffset + valid.byteLength,
  );
  assert.equal(isUtf8(exactArrayBuffer), true);
  assert.throws(
    () => isUtf8(new DataView(valid.buffer, valid.byteOffset, valid.byteLength)),
    (error) => error.code === 'ERR_INVALID_ARG_TYPE',
  );
});

test('atob/btoa 操作 Latin-1 二进制字符串，不是通用 Unicode 编码器', () => {
  assert.equal(btoa('ABC'), 'QUJD');
  assert.equal(atob('QUJD'), 'ABC');
  assert.equal(btoa('\xff'), '/w==');
  assert.equal(atob('/w==').charCodeAt(0), 255);
  assert.throws(() => btoa('中文'), {
    name: 'InvalidCharacterError',
  });

  assert.equal(Buffer.from('中文').toString('base64'), '5Lit5paH');
});

test('Blob 保存不可变字节快照，并支持 text/bytes/arrayBuffer/slice', async () => {
  const source = Buffer.from('hello world');
  const blob = new Blob([source], { type: 'text/plain' });
  source.fill(0);

  assert.equal(blob.size, 11);
  assert.equal(blob.type, 'text/plain');
  assert.equal(await blob.text(), 'hello world');
  assert.deepEqual([...await blob.bytes()], [...Buffer.from('hello world')]);
  assert.equal(Buffer.from(await blob.arrayBuffer()).toString(), 'hello world');
  assert.equal(await blob.slice(6, 11, 'text/custom').text(), 'world');
});

test('Blob object URL 在当前进程注册，可显式解析和撤销', async () => {
  const blob = new Blob(['payload']);
  const url = URL.createObjectURL(blob);

  try {
    assert.equal(url.startsWith('blob:nodedata:'), true);
    const resolved = resolveObjectURL(url);
    assert.notEqual(resolved, blob);
    assert.equal(resolved.size, blob.size);
    assert.equal(await resolved.text(), 'payload');
  } finally {
    URL.revokeObjectURL(url);
  }
  assert.equal(resolveObjectURL(url), undefined);
});
