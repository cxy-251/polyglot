// 运行时能力、版本与特性检测。
// 共同问题：代码如何识别当前实现和版本；如何检测某项能力是否真正存在；
// 何时应检测行为或接口而不是脆弱地比较版本字符串。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/nodejs/node_core/07_process_system_and_cli/
// polyglot-related+: test_062_process_metadata_environment_cwd_resources_and_builtin_access.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

test('运行时与组件版本由结构化字段分别报告', () => {
  const version = process.versions.node.split('.').map(Number);

  assert.equal(version.length, 3);
  assert.ok(version.every(Number.isInteger));
  assert.equal(process.release.name, 'node');
  assert.equal(typeof process.versions.v8, 'string');
  assert.equal(Number.isInteger(Number(process.versions.modules)), true);
  assert.notEqual(process.versions.node, process.versions.v8);

  assert.equal('24.18.0' < '9.0.0', true);
  // 字符串比较会把 24 错判为小于 9；需要比较版本时应先解析字段，能力分支则直接探测接口。
});

test('标准内置模块可通过运行时接口检测并取得', () => {
  const fileSystem = process.getBuiltinModule('node:fs');

  assert.equal(typeof fileSystem.readFile, 'function');
  assert.equal(process.getBuiltinModule('node:not-real'), undefined);
});

test('语法协议通过属性存在性检测', () => {
  assert.equal(typeof Symbol.dispose, 'symbol');
  assert.equal(typeof DisposableStack, 'function');

  // 版本满足下限不代表每个可选宿主 API 都启用；直接检查需要的接口更准确。
});

test('权限模型是否启用与 API 是否存在是不同问题', () => {
  if (process.permission === undefined) {
    assert.equal(process.permission, undefined);
  } else {
    assert.equal(typeof process.permission.has, 'function');
  }

  // 普通运行模式可能不暴露 process.permission；测试不通过启动额外权限模式制造假设。
});
