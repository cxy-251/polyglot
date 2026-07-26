// 进程环境与子进程输入输出。
// 共同问题：环境、工作目录和参数属于谁；如何向子进程传入数据并取得输出与退出状态；
// 哪些能力属于语言标准库，哪些依赖运行时或操作系统。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: process_environment_and_subprocess_io
// polyglot-related: languages/nodejs/node_core/07_process_system_and_cli/
// polyglot-related+: test_065_child_process_spawn_exec_exec_file_sync_abort_and_disposal.mjs

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

test('子进程环境可由调用方创建独立映射', () => {
  const result = spawnSync(
    process.execPath,
    ['-e', "process.stdout.write(process.env.POLYGLOT_VALUE)"],
    {
      encoding: 'utf8',
      env: { ...process.env, POLYGLOT_VALUE: 'child' },
    },
  );

  assert.equal(result.status, 0);
  assert.equal(result.stdout, 'child');
  assert.notEqual(process.env.POLYGLOT_VALUE, 'child');
});

test('子进程工作目录不改变调用方 cwd', (t) => {
  const original = process.cwd();
  const directory = mkdtempSync(path.join(os.tmpdir(), 'polyglot-concept-cwd-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const result = spawnSync(process.execPath, ['-e', 'process.stdout.write(process.cwd())'], {
    cwd: directory,
    encoding: 'utf8',
  });

  assert.equal(result.stdout, directory);
  assert.equal(process.cwd(), original);
});

test('spawnSync 明确返回 stdin、stdout 与退出状态', () => {
  const result = spawnSync(
    process.execPath,
    ['-e', "process.stdin.on('data', chunk => process.stdout.write(chunk.toString().toUpperCase()))"],
    { input: 'hello', encoding: 'utf8' },
  );

  assert.equal(result.status, 0);
  assert.equal(result.signal, null);
  assert.equal(result.stdout, 'HELLO');
});

test('参数数组不会经过 shell 展开', () => {
  const result = spawnSync(
    process.execPath,
    ['-e', 'process.stdout.write(process.argv[1])', 'a b; $HOME'],
    { encoding: 'utf8' },
  );

  assert.equal(result.stdout, 'a b; $HOME');
});
