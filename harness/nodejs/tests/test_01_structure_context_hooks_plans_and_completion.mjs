// polyglot-harness:
// - nodejs.core.node-test-test-context-name-full-name-file-path-worker-id-and-signal
// - nodejs.core.node-test-subtests-await-and-return-contract
// - nodejs.core.node-test-parent-hooks-before-before-each-after-each-after-order
// - nodejs.core.node-test-plan-counts-context-assertions-and-subtests
// - nodejs.core.node-test-concurrent-subtests-single-threaded-scheduling
// - nodejs.core.node-test-callback-completion-style
// - nodejs.core.node-test-wait-for-retry-value-and-timeout-options
// - nodejs.core.node-test-describe-it-suite-aliases-and-suite-context

import assert from 'node:assert/strict';
import test, { describe, it } from 'node:test';

test('TestContext 提供层级名、根测试文件、worker 编号和统一取消信号', async (t) => {
  assert.equal(t.name, 'TestContext 提供层级名、根测试文件、worker 编号和统一取消信号');
  assert.equal(t.fullName, t.name);
  assert.match(
    t.filePath,
    /test_01_structure_context_hooks_plans_and_completion\.mjs$/,
  );
  assert.equal(t.workerId, Number(process.env.NODE_TEST_WORKER_ID));
  assert.ok(t.signal instanceof AbortSignal);
  assert.equal(t.signal.aborted, false);

  await t.test('nested metadata', (child) => {
    assert.equal(child.name, 'nested metadata');
    assert.equal(child.fullName, `${t.name} > nested metadata`);
    assert.equal(child.filePath, t.filePath);
    assert.equal(child.workerId, t.workerId);
  });
  // filePath 始终指启动发现的根测试文件，即使测试由它导入的辅助模块注册。
});

test('父测试的 hooks 包围每个子测试，并在父测试完成前执行 after', async (t) => {
  const events = [];
  await t.test('hook scope', async (scope) => {
    scope.before(() => events.push('before'));
    scope.beforeEach((child) => events.push(`beforeEach:${child.name}`));
    scope.afterEach((child) => events.push(`afterEach:${child.name}`));
    scope.after(() => events.push('after'));

    await scope.test('first', () => events.push('body:first'));
    await scope.test('second', () => events.push('body:second'));
  });

  assert.deepEqual(events, [
    'before',
    'beforeEach:first',
    'body:first',
    'afterEach:first',
    'beforeEach:second',
    'body:second',
    'afterEach:second',
    'after',
  ]);
});

test('plan 只自动统计 t.assert 和子测试，不统计独立导入的 assert', async (t) => {
  t.plan(4);
  t.assert.equal(2 + 2, 4);
  t.assert.deepEqual({ ready: true }, { ready: true });
  assert.equal('这次断言不会计入 plan', '这次断言不会计入 plan');
  await t.test('first planned subtest');
  await t.test('second planned subtest');
  // plan 能发现未执行的异步断言；若使用 node:assert 裸函数，runner 无法自动计数。
});

test('并发子测试共享一个事件循环，Promise.all 等待全部完成', { concurrency: 2 }, async (t) => {
  const started = [];
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  const run = (name) => t.test(name, async () => {
    started.push(name);
    if (started.length === 2) release();
    await gate;
  });

  await Promise.all([run('first'), run('second')]);
  assert.deepEqual(new Set(started), new Set(['first', 'second']));
  // concurrency 是同线程异步调度，不会让 CPU 密集型 JavaScript 自动使用多个核心。
});

test('callback 风格只有调用 done 才完成，适合仍采用 Node 风格回调的 API', async (t) => {
  const events = [];
  await t.test('callback child', (child, done) => {
    assert.equal(child.signal.aborted, false);
    queueMicrotask(() => {
      events.push('callback');
      done();
    });
  });
  assert.deepEqual(events, ['callback']);
  // callback 测试不要再返回 Promise；混用两种完成协议会让错误归属和结束时机含糊。
});

test('waitFor 重试抛错的条件并把最后一次成功返回值传给调用者', async (t) => {
  let attempts = 0;
  const value = await t.waitFor(() => {
    attempts += 1;
    if (attempts < 2) throw new Error('not ready');
    return { state: 'ready' };
  }, { interval: 1, timeout: 100 });

  assert.deepEqual(value, { state: 'ready' });
  assert.equal(attempts, 2);
  // waitFor 的成功条件是“不抛错/不拒绝”，不是返回 truthy；返回 false 也会立即成功。
});

describe('describe 是 suite 的 BDD 别名', (suiteContext) => {
  assert.equal(suiteContext.name, 'describe 是 suite 的 BDD 别名');
  assert.equal(suiteContext.fullName, suiteContext.name);
  assert.match(suiteContext.filePath, /test_01_structure_context_hooks_plans/);
  assert.ok(suiteContext.signal instanceof AbortSignal);

  it('it 是 test 的 BDD 别名', (t) => {
    assert.equal(t.name, 'it 是 test 的 BDD 别名');
    assert.equal(t.fullName, `${suiteContext.name} > ${t.name}`);
  });
});
