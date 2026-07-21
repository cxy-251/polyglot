// polyglot-covers:
// - nodejs.core.node-test-cli-skip-todo-expect-failure-and-precedence
// - nodejs.core.node-test-cli-only-flag-and-only-is-not-default-focus
// - nodejs.core.node-test-cli-name-and-skip-pattern-body-selection
// - nodejs.core.node-test-extraneous-asynchronous-activity-file-failure
// - nodejs.core.node-test-global-setup-teardown-lifecycle
// - nodejs.core.node-test-programmatic-run-files-env-argv-pattern-and-setup
// - nodejs.core.node-test-tests-stream-event-types-metadata-correlation-and-summary
// - nodejs.core.node-test-reporters-spec-tap-dot-and-junit-structural-output
// - nodejs.core.node-test-custom-reporter-async-generator
// - nodejs.core.node-test-multiple-reporters-and-paired-destinations
// - nodejs.core.node-test-coverage-report-include-and-line-threshold
// - nodejs.core.node-test-rerun-failures-state-file-and-attempt-selection

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

function cleanEnvironment(overrides = {}) {
  const environment = { ...process.env, ...overrides };
  delete environment.NODE_TEST_CONTEXT;
  delete environment.NODE_TEST_WORKER_ID;
  return environment;
}

function runNode(directory, arguments_, overrides = {}) {
  return spawnSync(process.execPath, ['--no-warnings', ...arguments_], {
    cwd: directory,
    encoding: 'utf8',
    env: cleanEnvironment(overrides),
  });
}

test('CLI 状态标记与 only、name pattern、skip pattern 决定哪些测试体执行', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-selection-'));
  const fixture = join(directory, 'selection.test.mjs');
  writeFileSync(fixture, String.raw`
import test from 'node:test';

test('ordinary alpha', () => console.log('BODY:alpha'));
test.only('focused beta', () => console.log('BODY:beta'));
test.skip('skipped gamma', () => { throw new Error('skip body must not execute'); });
test.todo('todo delta', () => { throw new Error('todo failures do not fail the run'); });
test('expected epsilon', {
  expectFailure: { label: 'documented defect', match: /planned failure/ },
}, () => {
  throw new Error('planned failure');
});
test('dynamic skip zeta', (t) => {
  t.skip('runtime capability missing');
  console.log('BODY:skip-continues');
});
`);

  try {
    const ordinary = runNode(directory, ['--test', '--test-reporter=tap', fixture]);
    assert.equal(ordinary.status, 0, ordinary.stderr || ordinary.stdout);
    assert.match(ordinary.stdout, /BODY:alpha/);
    assert.match(ordinary.stdout, /BODY:beta/);
    assert.match(ordinary.stdout, /BODY:skip-continues/);
    assert.match(ordinary.stdout, /documented defect/);
    assert.match(ordinary.stdout, /runtime capability missing/);
    // only 只是标记；没有 --test-only 时不会悄悄屏蔽普通测试。

    const focused = runNode(directory, [
      '--test',
      '--test-only',
      '--test-reporter=tap',
      fixture,
    ]);
    assert.equal(focused.status, 0, focused.stderr || focused.stdout);
    assert.match(focused.stdout, /BODY:beta/);
    assert.doesNotMatch(focused.stdout, /BODY:alpha/);

    const patterned = runNode(directory, [
      '--test',
      '--test-name-pattern=alpha|beta',
      '--test-skip-pattern=beta',
      '--test-reporter=tap',
      fixture,
    ]);
    assert.equal(patterned.status, 0, patterned.stderr || patterned.stdout);
    assert.match(patterned.stdout, /BODY:alpha/);
    assert.doesNotMatch(patterned.stdout, /BODY:beta/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('测试结束后的未捕获异步错误归为文件失败，而不会伪装成通过', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-extraneous-'));
  const fixture = join(directory, 'extraneous.test.mjs');
  writeFileSync(fixture, String.raw`
import test from 'node:test';

test('body finishes before scheduled work', () => {
  setImmediate(() => {
    throw new Error('late asynchronous failure');
  });
});
`);

  try {
    const result = runNode(directory, ['--test', '--test-reporter=tap', fixture]);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /late asynchronous failure/);
    assert.match(result.stdout, /asynchronous activity|uncaughtException/i);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
  // runner 能归属异步越界错误，但正确做法仍是返回或 await 测试启动的所有异步工作。
});

test('global setup 与 teardown 在所有测试文件外层各执行一次', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-global-'));
  const events = join(directory, 'events.txt');
  const setup = join(directory, 'global.mjs');
  const first = join(directory, 'first.test.mjs');
  const second = join(directory, 'second.test.mjs');
  writeFileSync(setup, String.raw`
import { appendFileSync } from 'node:fs';
export function globalSetup() {
  appendFileSync(process.env.EVENT_FILE, 'setup\n');
}
export function globalTeardown() {
  appendFileSync(process.env.EVENT_FILE, 'teardown\n');
}
`);
  writeFileSync(first, String.raw`
import { appendFileSync } from 'node:fs';
import test from 'node:test';
test('first', () => appendFileSync(process.env.EVENT_FILE, 'first\n'));
`);
  writeFileSync(second, String.raw`
import { appendFileSync } from 'node:fs';
import test from 'node:test';
test('second', () => appendFileSync(process.env.EVENT_FILE, 'second\n'));
`);

  try {
    const result = runNode(
      directory,
      [
        '--test',
        `--test-global-setup=${setup}`,
        '--test-concurrency=1',
        '--test-reporter=tap',
        first,
        second,
      ],
      { EVENT_FILE: events },
    );
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.deepEqual(readFileSync(events, 'utf8').trim().split('\n'), [
      'setup',
      'first',
      'second',
      'teardown',
    ]);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('run() 返回 TestsStream，并把文件、环境、参数和名称过滤传给隔离进程', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-programmatic-'));
  const fixture = join(directory, 'programmatic-fixture.test.mjs');
  const driver = join(directory, 'driver.mjs');
  writeFileSync(fixture, String.raw`
import assert from 'node:assert/strict';
import test from 'node:test';

test('kept case', () => {
  assert.equal(process.env.RUNNER_VALUE, 'from-run');
  assert.ok(process.argv.includes('--payload'));
  console.log('fixture-output');
});
test('dropped case', () => {
  throw new Error('name filtering should omit this body');
});
`);
  writeFileSync(driver, String.raw`
import assert from 'node:assert/strict';
import { run } from 'node:test';
import { fileURLToPath } from 'node:url';

let setupCalled = false;
const events = [];
const fixture = fileURLToPath(new URL('./programmatic-fixture.test.mjs', import.meta.url));
const stream = run({
  files: [fixture],
  concurrency: 1,
  env: { RUNNER_VALUE: 'from-run' },
  argv: ['--payload'],
  testNamePatterns: /kept/,
  setup(testsStream) {
    setupCalled = typeof testsStream.on === 'function';
  },
});
for await (const event of stream) events.push(event);

assert.equal(setupCalled, true);
const passed = events.find(
  (event) => event.type === 'test:pass' && event.data.name === 'kept case'
);
assert.ok(passed);
assert.equal(typeof passed.data.testId, 'number');
assert.equal(typeof passed.data.testNumber, 'number');
assert.equal(typeof passed.data.line, 'number');
assert.match(passed.data.file, /programmatic-fixture\.test\.mjs$/);
assert.ok(events.some(
  (event) => event.type === 'test:stdout' && /fixture-output/.test(event.data.message)
));
assert.ok(events.some((event) => event.type === 'test:complete'));
const summaries = events.filter((event) => event.type === 'test:summary');
assert.equal(summaries.at(-1).data.success, true);
assert.equal(summaries.at(-1).data.counts.failed, 0);
console.log('PROGRAMMATIC_RUN_OK');
`);

  try {
    const result = runNode(directory, [driver]);
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(result.stdout, /PROGRAMMATIC_RUN_OK/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
  // reporter 文本会随 Node 版本调整；自动化集成应消费 TestsStream 的结构化事件。
});

test('内置、自定义与多 reporter 分别面向人、协议和 CI 文件', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-reporters-'));
  const fixture = join(directory, 'reporters.test.mjs');
  const reporter = join(directory, 'reporter.mjs');
  const junitFile = join(directory, 'results.xml');
  writeFileSync(fixture, String.raw`
import test from 'node:test';
for (let index = 1; index <= 20; index += 1) {
  test('passing case ' + index, () => {});
}
`);
  writeFileSync(reporter, String.raw`
export default async function* reporter(source) {
  for await (const event of source) {
    if (event.type === 'test:pass') yield 'PASS:' + event.data.name + '\n';
    if (event.type === 'test:summary' && event.data.file === undefined) {
      yield 'SUMMARY:' + event.data.counts.failed + '\n';
    }
  }
}
`);

  try {
    const spec = runNode(directory, ['--test', '--test-reporter=spec', fixture]);
    assert.equal(spec.status, 0, spec.stderr || spec.stdout);
    assert.match(spec.stdout, /passing case 1/);

    const tap = runNode(directory, ['--test', '--test-reporter=tap', fixture]);
    assert.equal(tap.status, 0, tap.stderr || tap.stdout);
    assert.match(tap.stdout, /^TAP version 13/m);
    assert.match(tap.stdout, /1\.\.20/);

    const dot = runNode(directory, ['--test', '--test-reporter=dot', fixture]);
    assert.equal(dot.status, 0, dot.stderr || dot.stdout);
    assert.match(dot.stdout.replaceAll('\n', ''), /^\.{20}$/);

    const junit = runNode(directory, ['--test', '--test-reporter=junit', fixture]);
    assert.equal(junit.status, 0, junit.stderr || junit.stdout);
    assert.match(junit.stdout, /<testsuites/);
    assert.match(junit.stdout, /<testcase/);

    const custom = runNode(directory, [
      '--test',
      `--test-reporter=${reporter}`,
      fixture,
    ]);
    assert.equal(custom.status, 0, custom.stderr || custom.stdout);
    assert.match(custom.stdout, /PASS:passing case 1/);
    assert.match(custom.stdout, /SUMMARY:0/);

    const multiple = runNode(directory, [
      '--test',
      '--test-reporter=spec',
      '--test-reporter=junit',
      '--test-reporter-destination=stdout',
      `--test-reporter-destination=${junitFile}`,
      fixture,
    ]);
    assert.equal(multiple.status, 0, multiple.stderr || multiple.stdout);
    assert.match(multiple.stdout, /passing case 1/);
    assert.match(readFileSync(junitFile, 'utf8'), /<testsuites/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('内置覆盖率报告能限定源文件，并用阈值把质量门槛转成退出状态', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-coverage-'));
  const source = join(directory, 'classify.mjs');
  const fixture = join(directory, 'coverage.test.mjs');
  writeFileSync(source, String.raw`
export function classify(value) {
  if (value > 0) return 'positive';
  return 'other';
}
`);
  writeFileSync(fixture, String.raw`
import assert from 'node:assert/strict';
import test from 'node:test';
import { classify } from './classify.mjs';
test('positive branch', () => assert.equal(classify(1), 'positive'));
`);

  try {
    const report = runNode(directory, [
      '--test',
      '--experimental-test-coverage',
      `--test-coverage-include=${source}`,
      '--test-reporter=tap',
      fixture,
    ]);
    assert.equal(report.status, 0, report.stderr || report.stdout);
    assert.match(report.stdout, /classify\.mjs/);
    assert.match(report.stdout, /coverage report/i);

    const gated = runNode(directory, [
      '--test',
      '--experimental-test-coverage',
      `--test-coverage-include=${source}`,
      '--test-coverage-lines=100',
      '--test-reporter=tap',
      fixture,
    ]);
    assert.equal(gated.status, 1);
    assert.match(gated.stdout, /line coverage|coverage/i);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('rerun failures 状态文件让下一次只重跑尚未成功的测试', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-test-rerun-'));
  const fixture = join(directory, 'rerun.test.mjs');
  const state = join(directory, 'rerun-state.json');
  writeFileSync(fixture, String.raw`
import assert from 'node:assert/strict';
import test from 'node:test';

test('already stable', () => console.log('BODY:stable'));
test('eventually repaired', () => {
  console.log('BODY:eventual');
  assert.equal(process.env.REPAIRED, 'yes');
});
`);

  try {
    const first = runNode(
      directory,
      ['--test', `--test-rerun-failures=${state}`, '--test-reporter=tap', fixture],
      { REPAIRED: 'no' },
    );
    assert.equal(first.status, 1);
    assert.match(first.stdout, /BODY:stable/);
    assert.match(first.stdout, /BODY:eventual/);
    assert.equal(existsSync(state), true);
    assert.ok(JSON.parse(readFileSync(state, 'utf8')).length >= 1);

    const second = runNode(
      directory,
      ['--test', `--test-rerun-failures=${state}`, '--test-reporter=tap', fixture],
      { REPAIRED: 'yes' },
    );
    assert.equal(second.status, 0, second.stderr || second.stdout);
    assert.doesNotMatch(second.stdout, /BODY:stable/);
    assert.match(second.stdout, /BODY:eventual/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
  // 状态键包含文件位置；移动测试或改变定义顺序后，应删除旧状态并重新建立基线。
});
