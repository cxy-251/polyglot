// 路径规范化与解析。
// 共同问题：路径操作是纯词法计算还是访问文件系统；相对路径以什么为基准；
// 规范化、绝对化与解析符号链接是否等价。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: path_normalization_and_resolution
// polyglot-related: languages/nodejs/node_core/03_files_paths_and_urls/
// polyglot-related+: test_041_path_posix_win32_normalization_parsing_and_matching.mjs

import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

test('normalize 和 join 是不检查存在性的词法操作', () => {
  assert.equal(path.posix.normalize('workspace/../result.txt'), 'result.txt');
  assert.equal(path.posix.join('/base', 'child'), '/base/child');
});

test('resolve 从右向左取得绝对基准', () => {
  assert.equal(path.posix.resolve('/base', 'child'), '/base/child');
  assert.equal(path.posix.resolve('/base', '/replacement'), '/replacement');
});

test('win32 与 posix 路径规则可被显式选择', () => {
  assert.equal(path.win32.basename('C:\\work\\file.txt'), 'file.txt');
  assert.equal(path.posix.basename('C:\\work\\file.txt'), 'C:\\work\\file.txt');
});

test('文件 URL 与路径需要显式转换', () => {
  const original = '/tmp/polyglot file.txt';
  const url = pathToFileURL(original);

  assert.equal(url.protocol, 'file:');
  assert.equal(url.pathname.includes('%20'), true);
  assert.equal(fileURLToPath(url), original);

  // URL percent-encoding 与平台路径语法不是可互换的字符串约定。
});
