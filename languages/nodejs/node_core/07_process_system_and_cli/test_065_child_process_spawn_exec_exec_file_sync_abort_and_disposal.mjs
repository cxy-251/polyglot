// polyglot-covers:
// - nodejs.core.child-process-spawn-arguments-env-cwd-and-stdio
// - nodejs.core.child-process-exit-and-close-events
// - nodejs.core.child-process-exec-shell-command
// - nodejs.core.child-process-exec-file-argument-boundary
// - nodejs.core.child-process-promisified-exec-and-exec-file
// - nodejs.core.child-process-max-buffer-error
// - nodejs.core.child-process-spawn-sync-exec-sync-and-exec-file-sync
// - nodejs.core.child-process-abort-signal
// - nodejs.core.child-process-symbol-dispose
// - nodejs.core.child-process-spawn-error

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  exec,
  execFile,
  execFileSync,
  execSync,
  spawn,
  spawnSync,
} from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';
import { promisify } from 'node:util';

const execAsync = promisify(exec);
const execFileAsync = promisify(execFile);

function collectChild(child) {
  const stdout = [];
  const stderr = [];
  child.stdout?.on('data', (chunk) => stdout.push(chunk));
  child.stderr?.on('data', (chunk) => stderr.push(chunk));
  return new Promise((resolve) => {
    child.once('close', (code, signal) => resolve({
      code,
      signal,
      stdout: Buffer.concat(stdout).toString(),
      stderr: Buffer.concat(stderr).toString(),
    }));
  });
}

test('spawn 用参数数组、env、cwd 和独立 stdio 启动进程', async () => {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-child-'));
  try {
    const source = `
      console.log(JSON.stringify({
        argument: process.argv[1],
        env: process.env.POLYGLOT_CHILD_VALUE,
        cwd: process.cwd(),
      }));
      console.error('child stderr');
    `;
    const child = spawn(process.execPath, ['-e', source, 'literal argument'], {
      cwd: root,
      env: {
        ...process.env,
        POLYGLOT_CHILD_VALUE: 'from parent',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const eventOrder = [];
    child.on('spawn', () => eventOrder.push('spawn'));
    child.on('exit', () => eventOrder.push('exit'));
    child.on('close', () => eventOrder.push('close'));
    const result = await collectChild(child);

    assert.equal(result.code, 0);
    assert.equal(result.signal, null);
    assert.deepEqual(JSON.parse(result.stdout), {
      argument: 'literal argument',
      env: 'from parent',
      cwd: root,
    });
    assert.equal(result.stderr, 'child stderr\n');
    assert.deepEqual(eventOrder, ['spawn', 'exit', 'close']);
    assert.equal(child.exitCode, 0);
    assert.equal(child.signalCode, null);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('exec 解析 shell 字符串；execFile 把元字符作为普通 argv 数据', async () => {
  const command = `${JSON.stringify(process.execPath)} -p "6 * 7"`;
  const shellResult = await execAsync(command);
  assert.equal(shellResult.stdout.trim(), '42');
  assert.equal(shellResult.stderr, '');

  const literal = 'value; echo must-not-run';
  const fileResult = await execFileAsync(
    process.execPath,
    ['-p', 'process.argv[1]', literal],
  );
  assert.equal(fileResult.stdout.trim(), literal);
  assert.equal(fileResult.stderr, '');
  // 用户输入应作为 execFile/spawn 的独立参数；拼进 exec 字符串会获得 shell 语义。
});

test('execFile 的 maxBuffer 限制累计输出，超限错误仍携带已捕获内容', async () => {
  await assert.rejects(
    execFileAsync(
      process.execPath,
      ['-e', `process.stdout.write('x'.repeat(2048))`],
      { maxBuffer: 100 },
    ),
    (error) => {
      assert.equal(error.code, 'ERR_CHILD_PROCESS_STDIO_MAXBUFFER');
      assert.equal(error.cmd.includes(process.execPath), true);
      assert.ok(error.stdout.length >= 100);
      return true;
    },
  );
  // maxBuffer 按字节边界工作；多字节文本还要考虑编码解码时的完整字符处理。
});

test('同步 API 阻塞事件循环，但在短小启动脚本中返回完整结果对象', () => {
  const spawned = spawnSync(
    process.execPath,
    ['-e', `console.log('out'); console.error('err')`],
    { encoding: 'utf8' },
  );
  assert.equal(spawned.status, 0);
  assert.equal(spawned.signal, null);
  assert.equal(spawned.error, undefined);
  assert.equal(spawned.stdout, 'out\n');
  assert.equal(spawned.stderr, 'err\n');

  assert.equal(
    execFileSync(process.execPath, ['-p', '21 * 2'], { encoding: 'utf8' }).trim(),
    '42',
  );
  const command = `${JSON.stringify(process.execPath)} -p "40 + 2"`;
  assert.equal(execSync(command, { encoding: 'utf8' }).trim(), '42');

  const failed = spawnSync(process.execPath, ['-e', 'process.exit(9)']);
  assert.equal(failed.status, 9);
  assert.equal(failed.signal, null);
});

test('AbortSignal 让 spawn 发出 AbortError，并用 killSignal 终止子进程', async () => {
  const controller = new AbortController();
  const reason = new Error('cancel child');
  const child = spawn(process.execPath, ['-e', `
    console.log('ready');
    process.stdin.resume();
  `], {
    signal: controller.signal,
    killSignal: 'SIGTERM',
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  await once(child.stdout, 'data');
  const childError = once(child, 'error');
  const childClosed = new Promise((resolve) => child.once('close', (...args) => resolve(args)));

  controller.abort(reason);
  const [error] = await childError;
  const [code, signal] = await childClosed;
  assert.equal(error.name, 'AbortError');
  assert.equal(error.code, 'ABORT_ERR');
  assert.equal(error.cause, reason);
  assert.equal(code, null);
  assert.equal(signal, 'SIGTERM');
});

test('Symbol.dispose 等价于发送 SIGTERM，killed 不表示 close 已发生', async () => {
  const child = spawn(process.execPath, ['-e', 'process.stdin.resume()'], {
    stdio: ['pipe', 'ignore', 'ignore'],
  });
  await once(child, 'spawn');
  const closed = new Promise((resolve) => child.once('close', (...args) => resolve(args)));

  assert.equal(child.killed, false);
  assert.equal(child[Symbol.dispose](), undefined);
  assert.equal(child.killed, true);
  const [code, signal] = await closed;
  assert.equal(code, null);
  assert.equal(signal, 'SIGTERM');
  assert.equal(child.signalCode, 'SIGTERM');
});

test('可执行文件不存在时先发 error，随后 close；不会产生有效 pid', async () => {
  const child = spawn('/definitely/missing/polyglot-command', []);
  const errorEvent = once(child, 'error');
  const closed = new Promise((resolve) => child.once('close', (...args) => resolve(args)));
  const [error] = await errorEvent;
  const [code, signal] = await closed;

  assert.equal(error.code, 'ENOENT');
  assert.equal(child.pid, undefined);
  assert.equal(code, -2);
  assert.equal(signal, null);
});
