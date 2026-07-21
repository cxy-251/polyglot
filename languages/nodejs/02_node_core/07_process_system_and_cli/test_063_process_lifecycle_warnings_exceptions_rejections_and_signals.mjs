// polyglot-covers:
// - nodejs.core.process-before-exit-and-exit-events
// - nodejs.core.process-exit-skips-before-exit-and-pending-work
// - nodejs.core.process-exit-code
// - nodejs.core.process-uncaught-exception-monitor-and-handler
// - nodejs.core.process-warning-event-code-and-detail
// - nodejs.core.process-strict-unhandled-rejection
// - nodejs.core.process-signal-events-and-kill
// - nodejs.core.process-child-exit-code-and-signal-code

import assert from 'node:assert/strict';
import test from 'node:test';

import { spawn } from 'node:child_process';
import { once } from 'node:events';

function spawnNode(source, options = {}) {
  return spawn(process.execPath, ['-e', source], {
    stdio: ['pipe', 'pipe', 'pipe'],
    ...options,
  });
}

function collectChild(child) {
  const stdout = [];
  const stderr = [];
  child.stdout?.on('data', (chunk) => stdout.push(chunk));
  child.stderr?.on('data', (chunk) => stderr.push(chunk));
  return once(child, 'close').then(([code, signal]) => ({
    code,
    signal,
    stdout: Buffer.concat(stdout).toString(),
    stderr: Buffer.concat(stderr).toString(),
  }));
}

test('beforeExit 可安排新工作并再次触发，exit 只能做同步收尾', async () => {
  const child = spawnNode(`
    let scheduled = false;
    process.on('beforeExit', (code) => {
      console.log('before:' + code);
      if (!scheduled) {
        scheduled = true;
        setImmediate(() => console.log('immediate'));
      }
    });
    process.on('exit', (code) => console.log('exit:' + code));
    process.exitCode = 7;
  `);
  const result = await collectChild(child);

  assert.equal(result.code, 7);
  assert.equal(result.signal, null);
  assert.deepEqual(result.stdout.trim().split('\n'), [
    'before:7',
    'immediate',
    'before:7',
    'exit:7',
  ]);
});

test('process.exit 立即进入 exit，跳过 beforeExit 和尚未执行的回调', async () => {
  const child = spawnNode(`
    process.on('beforeExit', () => console.log('before'));
    process.on('exit', (code) => process.stdout.write('exit:' + code));
    setImmediate(() => console.log('too late'));
    process.exit(3);
  `);
  const result = await collectChild(child);

  assert.equal(result.code, 3);
  assert.equal(result.stdout, 'exit:3');
  // 优先设置 exitCode 让事件循环自然排空；process.exit 可能截断异步日志和写入。
});

test('uncaughtExceptionMonitor 先观察，uncaughtException 决定是否继续退出', async () => {
  const child = spawnNode(`
    process.on('uncaughtExceptionMonitor', (error, origin) => {
      console.log('monitor:' + error.message + ':' + origin);
    });
    process.on('uncaughtException', (error, origin) => {
      console.log('handler:' + error.message + ':' + origin);
      process.exitCode = 23;
    });
    queueMicrotask(() => { throw new Error('boom'); });
  `);
  const result = await collectChild(child);

  assert.equal(result.code, 23);
  assert.deepEqual(result.stdout.trim().split('\n'), [
    'monitor:boom:uncaughtException',
    'handler:boom:uncaughtException',
  ]);
  assert.equal(result.stderr, '');
  // handler 只适合同步清理后退出；恢复正常服务可能让进程停留在未知状态。
});

test('warning 事件保留 name/code/detail，--no-warnings 只关闭默认打印', async () => {
  const child = spawn(
    process.execPath,
    ['--no-warnings', '-e', `
      process.on('warning', (warning) => {
        console.log(JSON.stringify({
          name: warning.name,
          message: warning.message,
          code: warning.code,
          detail: warning.detail,
        }));
      });
      process.emitWarning('careful', {
        type: 'PolyglotWarning',
        code: 'POLYGLOT_WARNING',
        detail: 'teaching detail',
      });
    `],
    { stdio: ['ignore', 'pipe', 'pipe'] },
  );
  const result = await collectChild(child);

  assert.equal(result.code, 0);
  assert.equal(result.stderr, '');
  assert.deepEqual(JSON.parse(result.stdout), {
    name: 'PolyglotWarning',
    message: 'careful',
    code: 'POLYGLOT_WARNING',
    detail: 'teaching detail',
  });
});

test('strict unhandled rejection 转成未捕获异常并让子进程失败', async () => {
  const child = spawnNode(`Promise.reject(new Error('unhandled'));`, {
    env: {
      ...process.env,
      NODE_OPTIONS: '--unhandled-rejections=strict',
    },
  });
  const result = await collectChild(child);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /Error: unhandled/);
  assert.match(result.stderr, /Promise\.reject/);
});

test('signal 事件可做同步收尾；kill 成功不等于目标已退出', async () => {
  const child = spawnNode(`
    process.on('SIGTERM', () => {
      console.log('received:SIGTERM');
      process.stdin.pause();
    });
    console.log('ready');
    process.stdin.resume();
  `);
  const output = [];
  child.stdout.on('data', (chunk) => output.push(chunk));
  await once(child.stdout, 'data');

  assert.equal(process.kill(child.pid, 'SIGTERM'), true);
  assert.equal(child.exitCode, null);
  const [code, signal] = await once(child, 'close');
  assert.equal(code, 0);
  assert.equal(signal, null);
  assert.match(Buffer.concat(output).toString(), /ready\nreceived:SIGTERM/);
  assert.equal(child.exitCode, 0);
  assert.equal(child.signalCode, null);
});
