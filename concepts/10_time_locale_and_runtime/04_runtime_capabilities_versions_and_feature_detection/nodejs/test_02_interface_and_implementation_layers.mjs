// 接口行为和实现层次。
// 共同问题：版本、实现和运行平台如何分开描述；如何验证真正可用的接口；
// 为什么字符串版本比较不能替代结构化版本与行为检测。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/nodejs/node_core/07_process_system_and_cli/
// polyglot-related+: test_062_process_metadata_environment_cwd_resources_and_builtin_access.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('结构化主版本避免词典序版本比较陷阱', () => {
  const [major, minor, patch] = process.versions.node.split('.').map(Number);

  assert.equal('24.18.0' < '9.0.0', true);
  assert.deepEqual([major, minor, patch], [24, 18, 0]);
});

test('Node、V8 与模块 ABI 是不同版本维度', () => {
  assert.equal(process.release.name, 'node');
  assert.equal(typeof process.versions.v8, 'string');
  assert.equal(Number.isInteger(Number(process.versions.modules)), true);
  assert.notEqual(process.versions.node, process.versions.v8);
});

test('接口检测后执行最小行为验证', () => {
  assert.equal(typeof import.meta.resolve, 'function');
  assert.equal(import.meta.resolve('node:fs'), 'node:fs');

  const events = [];
  {
    using resource = {
      [Symbol.dispose]() {
        events.push('disposed');
      },
    };
    assert.equal(resource[Symbol.dispose] instanceof Function, true);
  }
  assert.deepEqual(events, ['disposed']);
});
