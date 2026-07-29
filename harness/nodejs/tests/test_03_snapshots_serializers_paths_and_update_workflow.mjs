// polyglot-harness:
// - nodejs.core.node-test-snapshot-missing-baseline-failure-and-update-flag
// - nodejs.core.node-test-snapshot-full-name-counter-and-human-readable-file
// - nodejs.core.node-test-snapshot-custom-path-resolver
// - nodejs.core.node-test-snapshot-default-serializer-configuration
// - nodejs.core.node-test-snapshot-per-assertion-serializer-pipeline
// - nodejs.core.node-test-file-snapshot-explicit-path-single-value-and-raw-content
// - nodejs.core.node-test-snapshot-mismatch-diagnostics-and-intentional-update-workflow
// - nodejs.core.node-test-custom-assertion-registration-on-test-context

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

function childEnvironment(overrides = {}) {
  const environment = { ...process.env, ...overrides };
  // 父测试进程的内部消息通道不能传给嵌套 runner，否则子 runner 不向 stdout 报告。
  delete environment.NODE_TEST_CONTEXT;
  delete environment.NODE_TEST_WORKER_ID;
  return environment;
}

function runFixture(file, options = [], environment = {}) {
  return spawnSync(
    process.execPath,
    [
      '--no-warnings',
      '--test',
      '--test-concurrency=1',
      '--test-reporter=tap',
      ...options,
      file,
    ],
    {
      encoding: 'utf8',
      env: childEnvironment(environment),
    },
  );
}

test('snapshot 工作流先失败、显式更新、稳定比较，再有意接受新基线', () => {
  const directory = mkdtempSync(join(tmpdir(), 'polyglot-nodejs-snapshots-'));
  const snapshotDirectory = join(directory, 'snapshots');
  const fixture = join(directory, 'snapshot-workflow.test.mjs');
  const managedSnapshot = join(snapshotDirectory, 'managed.snapshot.cjs');
  const fileSnapshot = join(snapshotDirectory, 'response.md');
  mkdirSync(snapshotDirectory);
  writeFileSync(fixture, String.raw`
import assert from 'node:assert/strict';
import { dirname, join } from 'node:path';
import test, { assert as testAssertions, snapshot } from 'node:test';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
snapshot.setResolveSnapshotPath(() => join(directory, 'snapshots', 'managed.snapshot.cjs'));
snapshot.setDefaultSnapshotSerializers([
  (value) => JSON.stringify(value, Object.keys(value).sort()),
]);

testAssertions.register('isEven', (value, message) => {
  assert.equal(value % 2, 0, message);
});

test('managed snapshots use full name and a per-test counter', (t) => {
  const version = Number(process.env.SNAPSHOT_VALUE);
  t.assert.snapshot({ version, state: 'ready' });
  t.assert.snapshot({ version, state: 'cached' });
});

test('fileSnapshot writes one raw value to an explicit path', (t) => {
  t.assert.fileSnapshot(
    { title: 'response', lines: ['ready'] },
    join(directory, 'snapshots', 'response.md'),
    {
      serializers: [
        (value) => ['# ' + value.title, ...value.lines],
        (lines) => lines.join('\n') + '\n',
      ],
    },
  );
});

test('register adds a process-wide assertion to every TestContext', (t) => {
  t.plan(1);
  t.assert.isEven(4, 'value should be even');
});
`);

  try {
    const missing = runFixture(fixture, [], { SNAPSHOT_VALUE: '1' });
    assert.equal(missing.status, 1);
    assert.match(`${missing.stdout}\n${missing.stderr}`, /snapshot|ENOENT/i);

    const updated = runFixture(
      fixture,
      ['--test-update-snapshots'],
      { SNAPSHOT_VALUE: '1' },
    );
    assert.equal(updated.status, 0, updated.stderr || updated.stdout);
    assert.match(updated.stdout, /1\.\.3/);

    const managedText = readFileSync(managedSnapshot, 'utf8');
    assert.match(managedText, /managed snapshots use full name and a per-test counter 1/);
    assert.match(managedText, /managed snapshots use full name and a per-test counter 2/);
    assert.match(managedText, /\{"state":"ready","version":1\}/);
    assert.equal(readFileSync(fileSnapshot, 'utf8'), '# response\nready\n');

    const stable = runFixture(fixture, [], { SNAPSHOT_VALUE: '1' });
    assert.equal(stable.status, 0, stable.stderr || stable.stdout);

    const mismatch = runFixture(fixture, [], { SNAPSHOT_VALUE: '2' });
    assert.equal(mismatch.status, 1);
    assert.match(mismatch.stdout, /snapshot/i);

    const accepted = runFixture(
      fixture,
      ['--test-update-snapshots'],
      { SNAPSHOT_VALUE: '2' },
    );
    assert.equal(accepted.status, 0, accepted.stderr || accepted.stdout);
    assert.match(readFileSync(managedSnapshot, 'utf8'), /"version":2/);

    const newBaseline = runFixture(fixture, [], { SNAPSHOT_VALUE: '2' });
    assert.equal(newBaseline.status, 0, newBaseline.stderr || newBaseline.stdout);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
  // 更新快照是有意修改测试预期的评审动作，不应在普通测试命令中自动发生。
});
