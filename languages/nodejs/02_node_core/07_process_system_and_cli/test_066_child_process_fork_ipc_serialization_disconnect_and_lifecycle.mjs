// polyglot-covers:
// - nodejs.core.child-process-fork-node-module-and-arguments
// - nodejs.core.child-process-fork-ipc-channel
// - nodejs.core.child-process-send-message-and-callback
// - nodejs.core.child-process-json-serialization-boundary
// - nodejs.core.child-process-advanced-serialization
// - nodejs.core.child-process-ipc-map-set-bigint-buffer-and-error
// - nodejs.core.child-process-channel-ref-and-unref
// - nodejs.core.child-process-disconnect-events-and-connected-state
// - nodejs.core.child-process-fork-silent-stdio

import assert from 'node:assert/strict';
import test from 'node:test';

import { fork } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { once } from 'node:events';

async function makeChildModule(source) {
  const root = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-fork-'));
  const path = join(root, 'child.mjs');
  await writeFile(path, source);
  return { root, path };
}

function exitResult(child) {
  // silent: true 的管道由父进程消费；fork 的业务生命周期以 exit 为终点。
  // exit 与全部 stdio 关闭后的 close 顺序已在 spawn 案例中单独验证。
  child.stdout?.resume();
  child.stderr?.resume();
  return new Promise((resolve) => {
    child.once('exit', (code, signal) => resolve({ code, signal }));
  });
}

function send(child, message) {
  return new Promise((resolve, reject) => {
    child.send(message, (error) => {
      if (error) reject(error);
      else resolve();
    });
  });
}

function nextMessage(child) {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      child.off('message', onMessage);
      child.off('error', onError);
      child.off('exit', onEarlyExit);
    };
    const onMessage = (message) => {
      cleanup();
      resolve(message);
    };
    const onError = (error) => {
      cleanup();
      reject(error);
    };
    const onEarlyExit = (code, signal) => {
      cleanup();
      reject(new Error(`child exited before message: code=${code}, signal=${signal}`));
    };
    child.once('message', onMessage);
    child.once('error', onError);
    child.once('exit', onEarlyExit);
  });
}

test('fork 自动建立 IPC channel，并把模块参数与进程元数据交给子 Node', async () => {
  const fixture = await makeChildModule(`
    process.stdin.resume();
    process.on('message', () => {});
    process.on('disconnect', () => {
      process.stdin.pause();
      process.exit(0);
    });
    process.send({
      argument: process.argv[2],
      connected: process.connected,
      hasSend: typeof process.send === 'function',
      hasChannel: Boolean(process.channel),
      env: process.env.POLYGLOT_FORK_VALUE,
    });
  `);
  const child = fork(pathToFileURL(fixture.path), ['argument'], {
    silent: true,
    env: { ...process.env, POLYGLOT_FORK_VALUE: 'from parent' },
  });
  const exited = exitResult(child);

  try {
    const message = await nextMessage(child);
    assert.deepEqual(message, {
      argument: 'argument',
      connected: true,
      hasSend: true,
      hasChannel: true,
      env: 'from parent',
    });
    assert.equal(child.connected, true);
    assert.equal(typeof child.channel.ref, 'function');
    assert.equal(typeof child.channel.unref, 'function');
    child.channel.unref();
    child.channel.ref();

    const parentDisconnect = once(child, 'disconnect');
    child.stdin.end();
    child.disconnect();
    await parentDisconnect;
    assert.equal(child.connected, false);
    assert.deepEqual(await exited, { code: 0, signal: null });
  } finally {
    if (!child.killed && child.exitCode === null) child.kill();
    await rm(fixture.root, { recursive: true, force: true });
  }
});

test('默认 JSON serialization 会转换 Date，并拒绝 BigInt', async () => {
  const fixture = await makeChildModule(`
    process.on('message', (message) => {
      if (message.command === 'echo') process.send(message.value);
      if (message.command === 'stop') process.disconnect();
    });
  `);
  const child = fork(fixture.path, { silent: true, serialization: 'json' });
  const exited = exitResult(child);
  child.stdin.end();

  try {
    const echoed = nextMessage(child);
    await send(child, {
      command: 'echo',
      value: { createdAt: new Date('2020-01-02T03:04:05.000Z') },
    });
    assert.deepEqual(await echoed, {
      createdAt: '2020-01-02T03:04:05.000Z',
    });

    assert.throws(
      () => child.send({ value: 1n }),
      (error) => error instanceof TypeError && /BigInt/.test(error.message),
    );
    await send(child, { command: 'stop' });
    assert.deepEqual(await exited, { code: 0, signal: null });
  } finally {
    if (!child.killed && child.exitCode === null) child.kill();
    await rm(fixture.root, { recursive: true, force: true });
  }
});

test('advanced serialization 按 structured clone 传递 JSON 无法表达的内置类型', async () => {
  const fixture = await makeChildModule(`
    process.on('message', (message) => {
      process.send({
        map: message.map,
        set: message.set,
        big: message.big,
        bytes: message.bytes,
        error: message.error,
      });
      process.disconnect();
    });
  `);
  const child = fork(fixture.path, {
    silent: true,
    serialization: 'advanced',
  });
  const exited = exitResult(child);
  child.stdin.end();

  try {
    const response = nextMessage(child);
    await send(child, {
      map: new Map([['answer', 42]]),
      set: new Set(['a', 'b']),
      big: 9_007_199_254_740_993n,
      bytes: Buffer.from([1, 2, 3]),
      error: new TypeError('typed failure'),
    });
    const message = await response;

    assert.ok(message.map instanceof Map);
    assert.equal(message.map.get('answer'), 42);
    assert.ok(message.set instanceof Set);
    assert.deepEqual([...message.set], ['a', 'b']);
    assert.equal(message.big, 9_007_199_254_740_993n);
    assert.ok(Buffer.isBuffer(message.bytes));
    assert.deepEqual(message.bytes, Buffer.from([1, 2, 3]));
    assert.ok(message.error instanceof TypeError);
    assert.equal(message.error.message, 'typed failure');
    assert.deepEqual(await exited, { code: 0, signal: null });
  } finally {
    if (!child.killed && child.exitCode === null) child.kill();
    await rm(fixture.root, { recursive: true, force: true });
  }
  // advanced 更有表达力但不是 JSON 的超集，性能特征也不同，协议双方必须显式约定。
});
