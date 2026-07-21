// polyglot-covers:
// - nodejs.core.cluster-primary-and-worker-roles
// - nodejs.core.cluster-setup-primary-settings-and-setup-event
// - nodejs.core.cluster-scheduling-policy
// - nodejs.core.cluster-fork-workers-map-and-worker-state
// - nodejs.core.cluster-worker-process-and-ipc
// - nodejs.core.cluster-shared-server-handle
// - nodejs.core.cluster-worker-listening-message-disconnect-and-exit-events
// - nodejs.core.cluster-graceful-disconnect

import assert from 'node:assert/strict';
import test from 'node:test';

import { spawn } from 'node:child_process';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

async function runNode(modulePath, args = []) {
  const child = spawn(process.execPath, [modulePath, ...args], {
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', (chunk) => stdout.push(chunk));
  child.stderr.on('data', (chunk) => stderr.push(chunk));

  const result = await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('close', (code, signal) => resolve({ code, signal }));
  });
  return {
    ...result,
    stdout: Buffer.concat(stdout).toString(),
    stderr: Buffer.concat(stderr).toString(),
  };
}

const workerSource = `
  import cluster from 'node:cluster';
  import { createServer } from 'node:net';

  if (!cluster.isWorker || cluster.isPrimary || cluster.worker === undefined) {
    throw new Error('cluster worker role mismatch');
  }

  const server = createServer((socket) => {
    socket.end(JSON.stringify({
      workerId: cluster.worker.id,
      state: cluster.worker.state,
    }) + '\\n');
  });

  process.on('message', (message) => {
    if (message?.type !== 'ping') return;
    process.send({
      type: 'pong',
      workerId: cluster.worker.id,
      receivedMap: message.payload instanceof Map,
      argumentPresent: process.argv.includes('worker-argument'),
    });
  });

  server.listen({ host: '127.0.0.1', port: 0 });
`;

const primarySource = `
  import cluster from 'node:cluster';
  import { connect } from 'node:net';

  const workerFile = process.argv[2];

  function forkAndObserve() {
    const worker = cluster.fork({ POLYGLOT_CLUSTER_WORKER: 'yes' });
    const listening = new Promise((resolve, reject) => {
      worker.once('error', reject);
      worker.once('listening', resolve);
    });
    return { worker, listening };
  }

  function request(port) {
    return new Promise((resolve, reject) => {
      const socket = connect({ host: '127.0.0.1', port });
      let body = '';
      socket.setEncoding('utf8');
      socket.on('data', (chunk) => { body += chunk; });
      socket.once('end', () => resolve(JSON.parse(body)));
      socket.once('error', reject);
    });
  }

  function ping(worker) {
    return new Promise((resolve, reject) => {
      function onMessage(message) {
        if (message?.type !== 'pong') return;
        worker.off('error', reject);
        resolve(message);
      }
      worker.once('error', reject);
      worker.on('message', onMessage);
      worker.send(
        { type: 'ping', payload: new Map([['answer', 42]]) },
        (error) => {
          if (error) reject(error);
        },
      );
    });
  }

  async function main() {
    if (!cluster.isPrimary || cluster.isWorker || cluster.worker !== undefined) {
      throw new Error('cluster primary role mismatch');
    }

    let setupEvents = 0;
    cluster.on('setup', () => { setupEvents += 1; });
    cluster.schedulingPolicy = cluster.SCHED_RR;
    cluster.setupPrimary({
      exec: workerFile,
      args: ['worker-argument'],
      silent: true,
      serialization: 'advanced',
    });

    const entries = [forkAndObserve(), forkAndObserve()];
    const workers = entries.map(({ worker }) => worker);
    const addresses = await Promise.all(entries.map(({ listening }) => listening));
    const port = addresses[0].port;
    const beforeDisconnect = workers.map((worker) => ({
      id: worker.id,
      state: worker.state,
      connected: worker.isConnected(),
      dead: worker.isDead(),
      inWorkersMap: cluster.workers[worker.id] === worker,
      processPid: worker.process.pid,
    }));

    const pongs = await Promise.all(workers.map(ping));
    const replies = [];
    for (let index = 0; index < 8; index += 1) {
      replies.push(await request(port));
    }

    const exitEvents = workers.map((worker) => new Promise((resolve, reject) => {
      worker.once('error', reject);
      worker.once('exit', (code, signal) => resolve({ code, signal }));
    }));
    const disconnectEvents = workers.map((worker) => new Promise((resolve) => {
      worker.once('disconnect', resolve);
    }));
    await new Promise((resolve, reject) => {
      cluster.disconnect((error) => {
        if (error) reject(error);
        else resolve();
      });
    });
    await Promise.all(disconnectEvents);
    const exits = await Promise.all(exitEvents);

    console.log(JSON.stringify({
      primary: { isPrimary: cluster.isPrimary, isWorker: cluster.isWorker },
      setupEvents,
      settings: {
        execMatches: cluster.settings.exec === workerFile,
        args: cluster.settings.args,
        silent: cluster.settings.silent,
        serialization: cluster.settings.serialization,
      },
      schedulingRoundRobin: cluster.schedulingPolicy === cluster.SCHED_RR,
      addresses,
      beforeDisconnect,
      pongs,
      replies,
      exits,
      remainingWorkerIds: Object.keys(cluster.workers),
    }));
  }

  main().catch((error) => {
    for (const worker of Object.values(cluster.workers ?? {})) {
      worker.kill();
    }
    console.error(error);
    process.exitCode = 1;
  });
`;

test('cluster 在独立主进程中派生 Worker，并共享同一个 TCP 监听句柄', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'polyglot-nodejs-cluster-'));
  const workerPath = join(directory, 'worker.mjs');
  const primaryPath = join(directory, 'primary.mjs');
  try {
    await Promise.all([
      writeFile(workerPath, workerSource),
      writeFile(primaryPath, primarySource),
    ]);
    const result = await runNode(primaryPath, [workerPath]);
    assert.deepEqual(
      { code: result.code, signal: result.signal, stderr: result.stderr },
      { code: 0, signal: null, stderr: '' },
    );
    const report = JSON.parse(result.stdout);

    assert.deepEqual(report.primary, { isPrimary: true, isWorker: false });
    assert.ok(report.setupEvents >= 1);
    // setup 不是“配置文件只加载一次”的信号：显式 setupPrimary 会触发它，后续 fork
    // 在实现内部再次确认 primary 设置时也可能触发，因此只依赖事件至少发生一次。
    assert.deepEqual(report.settings, {
      execMatches: true,
      args: ['worker-argument'],
      silent: true,
      serialization: 'advanced',
    });
    assert.equal(report.schedulingRoundRobin, true);
    assert.equal(new Set(report.addresses.map(({ port }) => port)).size, 1);
    assert.ok(report.addresses.every(({ addressType }) => addressType === 4));

    assert.equal(report.beforeDisconnect.length, 2);
    assert.ok(report.beforeDisconnect.every((worker) => (
      worker.state === 'listening'
      && worker.connected
      && !worker.dead
      && worker.inWorkersMap
      && Number.isInteger(worker.processPid)
    )));
    assert.ok(report.pongs.every((pong) => pong.receivedMap && pong.argumentPresent));
    // SCHED_RR 在当前锁定的 Linux 工具链中把连续连接轮转给两个 Worker；
    // 这里只验证两个身份都实际服务过请求，不把精确的交替顺序写成脆弱契约。
    assert.deepEqual(
      new Set(report.replies.map(({ workerId }) => workerId)),
      new Set(report.beforeDisconnect.map(({ id }) => id)),
    );
    assert.ok(report.replies.every(({ state }) => state === 'listening'));
    assert.deepEqual(report.exits, [
      { code: 0, signal: null },
      { code: 0, signal: null },
    ]);
    assert.deepEqual(report.remainingWorkerIds, []);
    // cluster.disconnect 会先让共享 server 停止接收，再断开 IPC，适合优雅停机；
    // worker.kill() 则直接结束进程，应留给失败清理或无法正常退出的 Worker。
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
