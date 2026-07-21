// polyglot-covers:
// - nodejs.core.inspector-promises-session-connect-post-disconnect-and-reconnect
// - nodejs.core.inspector-runtime-evaluate-return-by-value-and-exception-details
// - nodejs.core.inspector-protocol-error-versus-evaluated-code-error
// - nodejs.core.inspector-remote-object-properties-groups-and-release
// - nodejs.core.inspector-notification-generic-and-method-specific-events
// - nodejs.core.inspector-callback-session-api
// - nodejs.core.inspector-cpu-profiler-workflow
// - nodejs.core.inspector-heap-sampling-profiler-workflow
// - nodejs.core.inspector-worker-connect-to-main-thread
// - nodejs.core.inspector-open-url-close-and-disposable-loopback-listener

import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { once } from 'node:events';
import { Session as CallbackSession } from 'node:inspector';
import { Session } from 'node:inspector/promises';
import { promisify } from 'node:util';
import { Worker } from 'node:worker_threads';
import test from 'node:test';

const execFileAsync = promisify(execFile);

async function withSession(run) {
  const session = new Session();
  session.connect();
  try {
    return await run(session);
  } finally {
    session.disconnect();
  }
}

test('Promises Session 连接当前 isolate，post 返回协议结果，断开后可重新连接', async () => {
  const session = new Session();
  await assert.rejects(
    session.post('Runtime.evaluate', { expression: '1 + 1' }),
    { code: 'ERR_INSPECTOR_NOT_CONNECTED' },
  );

  session.connect();
  const first = await session.post('Runtime.evaluate', {
    expression: '6 * 7',
    returnByValue: true,
  });
  assert.deepEqual(first.result, {
    type: 'number',
    value: 42,
    description: '42',
  });
  session.disconnect();

  await assert.rejects(
    session.post('Runtime.evaluate', { expression: '1 + 1' }),
    { code: 'ERR_INSPECTOR_NOT_CONNECTED' },
  );
  session.connect();
  const second = await session.post('Runtime.evaluate', {
    expression: 'typeof process',
    returnByValue: true,
  });
  assert.equal(second.result.value, 'object');
  session.disconnect();
  // reconnect 会建立全新 inspector 状态：先前启用的 domain、断点和对象组都不会保留。
});

test('Runtime.evaluate 中代码抛错仍是成功协议响应，未知协议方法才拒绝 post', async () => {
  await withSession(async (session) => {
    const evaluated = await session.post('Runtime.evaluate', {
      expression: 'throw new RangeError("out of range")',
    });
    assert.equal(evaluated.result.subtype, 'error');
    assert.match(evaluated.result.description, /RangeError: out of range/);
    assert.match(evaluated.exceptionDetails.text, /Uncaught/);
    assert.equal(typeof evaluated.exceptionDetails.exceptionId, 'number');

    await assert.rejects(
      session.post('Polyglot.noSuchMethod'),
      (error) => error.code === 'ERR_INSPECTOR_COMMAND'
        && error.message.includes('-32601'),
    );
  });
  // 调试对象代码失败属于 Runtime.evaluate 的数据；协议命令无效才是 post Promise 的拒绝。
});

test('远程对象用 objectId 查询属性，releaseObjectGroup 后句柄立即失效', async () => {
  await withSession(async (session) => {
    const { result } = await session.post('Runtime.evaluate', {
      expression: '({ answer: 42, nested: { ready: true } })',
      objectGroup: 'polyglot-temporary',
    });
    assert.equal(result.type, 'object');
    assert.equal(result.className, 'Object');
    assert.equal(typeof result.objectId, 'string');
    assert.equal('value' in result, false);

    const properties = await session.post('Runtime.getProperties', {
      objectId: result.objectId,
      ownProperties: true,
    });
    const answer = properties.result.find(({ name }) => name === 'answer');
    const nested = properties.result.find(({ name }) => name === 'nested');
    assert.equal(answer.value.value, 42);
    assert.equal(typeof nested.value.objectId, 'string');

    await session.post('Runtime.releaseObjectGroup', {
      objectGroup: 'polyglot-temporary',
    });
    await assert.rejects(
      session.post('Runtime.getProperties', { objectId: result.objectId }),
      { code: 'ERR_INSPECTOR_COMMAND' },
    );
  });
  // 不使用 returnByValue 时拿到的是 V8 堆对象句柄；长期调试器必须及时释放对象或对象组。
});

test('协议通知同时触发 inspectorNotification 总线和方法名专用事件', async () => {
  await withSession(async (session) => {
    const allMethods = [];
    const parsedScripts = [];
    session.on('inspectorNotification', ({ method }) => allMethods.push(method));
    session.on('Debugger.scriptParsed', ({ params }) => parsedScripts.push(params));

    await session.post('Debugger.enable');
    await session.post('Runtime.evaluate', {
      expression: 'globalThis.__polyglotInspected = 42;\n//# sourceURL=polyglot-inspected.js',
    });
    await session.post('Debugger.disable');

    assert.ok(allMethods.includes('Debugger.scriptParsed'));
    assert.ok(parsedScripts.some(({ url }) => url === 'polyglot-inspected.js'));
    assert.equal(globalThis.__polyglotInspected, 42);
    delete globalThis.__polyglotInspected;
  });
});

test('Callback Session 把协议错误放第一个参数，把命令结果放第二个参数', async () => {
  const session = new CallbackSession();
  session.connect();
  try {
    const response = await new Promise((resolve, reject) => {
      session.post(
        'Runtime.evaluate',
        { expression: '21 * 2', returnByValue: true },
        (error, result) => error ? reject(error) : resolve(result),
      );
    });
    assert.equal(response.result.value, 42);

    const protocolError = await new Promise((resolve) => {
      session.post('Polyglot.noSuchMethod', (error) => resolve(error));
    });
    assert.equal(protocolError.code, 'ERR_INSPECTOR_COMMAND');
  } finally {
    session.disconnect();
  }
});

test('Profiler domain 采集一段 CPU 工作，并返回 Chrome CPU Profile 对象', async () => {
  await withSession(async (session) => {
    await session.post('Profiler.enable');
    await session.post('Profiler.start');
    let checksum = 0;
    for (let index = 0; index < 30_000; index += 1) {
      checksum = (checksum + index) % 65_521;
    }
    const { profile } = await session.post('Profiler.stop');
    await session.post('Profiler.disable');

    assert.ok(profile.nodes.length > 0);
    assert.ok(profile.endTime >= profile.startTime);
    assert.ok(Array.isArray(profile.samples));
    assert.ok(Array.isArray(profile.timeDeltas));
    assert.ok(profile.nodes.some(({ callFrame }) => callFrame.functionName.length >= 0));
    assert.ok(checksum >= 0);
  });
});

test('HeapProfiler sampling 记录分配热点，不生成体积庞大的完整 heap snapshot', async () => {
  await withSession(async (session) => {
    await session.post('HeapProfiler.enable');
    await session.post('HeapProfiler.startSampling', {
      samplingInterval: 1_024,
      includeObjectsCollectedByMajorGC: true,
      includeObjectsCollectedByMinorGC: true,
    });
    const retained = Array.from({ length: 2_000 }, (_, index) => ({
      index,
      payload: `record-${index}-${'x'.repeat(64)}`,
    }));
    const { profile } = await session.post('HeapProfiler.stopSampling');
    await session.post('HeapProfiler.disable');

    assert.equal(typeof profile.head.callFrame.functionName, 'string');
    assert.ok(Array.isArray(profile.head.children));
    assert.ok(Array.isArray(profile.samples));
    assert.ok(profile.samples.length > 0);
    assert.equal(retained.length, 2_000);
  });
  // takeHeapSnapshot 会同步遍历整个堆且可能需要约两倍堆内存；常规热点采样优先 sampling。
});

test('connectToMainThread 只能从 worker 调用，并可在 worker 中检查主线程全局对象', async () => {
  const mainSession = new Session();
  assert.throws(
    () => mainSession.connectToMainThread(),
    { code: 'ERR_INSPECTOR_NOT_WORKER' },
  );

  const workerSource = `
    const { parentPort } = require('node:worker_threads');
    const { Session } = require('node:inspector/promises');
    (async () => {
      const session = new Session();
      session.connectToMainThread();
      const response = await session.post('Runtime.evaluate', {
        expression: 'globalThis.__polyglotWorkerInspected = 42',
        returnByValue: true,
      });
      session.disconnect();
      parentPort.postMessage(response.result.value);
    })().catch((error) => { throw error; });
  `;
  const worker = new Worker(workerSource, { eval: true });
  const [value] = await once(worker, 'message');
  const [exitCode] = await once(worker, 'exit');
  assert.equal(value, 42);
  assert.equal(exitCode, 0);
  assert.equal(globalThis.__polyglotWorkerInspected, 42);
  delete globalThis.__polyglotWorkerInspected;
});

test('open(0) 在隔离子进程监听动态回环端口，url/close/Disposable 反映生命周期', async () => {
  const script = `
    const inspector = require('node:inspector');
    const before = inspector.url() ?? null;
    const first = inspector.open(0, '127.0.0.1', false);
    const firstUrl = inspector.url();
    first[Symbol.dispose]();
    const afterDispose = inspector.url() ?? null;
    inspector.open(0, '127.0.0.1', false);
    const secondUrl = inspector.url();
    inspector.close();
    const afterClose = inspector.url() ?? null;
    process.stdout.write(JSON.stringify({
      before,
      firstUrl,
      afterDispose,
      secondUrl,
      afterClose,
    }));
  `;
  const { stdout, stderr } = await execFileAsync(
    process.execPath,
    ['--eval', script],
    { env: process.env },
  );
  const lifecycle = JSON.parse(stdout);
  assert.equal(lifecycle.before, null);
  assert.match(lifecycle.firstUrl, /^ws:\/\/127\.0\.0\.1:\d+\//);
  assert.equal(lifecycle.afterDispose, null);
  assert.match(lifecycle.secondUrl, /^ws:\/\/127\.0\.0\.1:\d+\//);
  assert.equal(lifecycle.afterClose, null);
  assert.match(stderr, /Debugger listening on ws:\/\/127\.0\.0\.1:/);
  // host 设为公网地址会暴露调试权限；示例固定回环地址且由系统选择空闲端口。
});
