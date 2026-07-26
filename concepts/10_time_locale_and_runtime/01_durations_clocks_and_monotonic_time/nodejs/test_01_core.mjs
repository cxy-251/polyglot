// 时长、时钟与单调时间。
// 共同问题：时长与时间点如何运算；墙上时钟和单调时钟分别回答什么；
// 测量经过时间是否依赖真实等待或日历时间。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/nodejs/node_core/10_diagnostics_and_testing/
// polyglot-related+: test_082_performance_timeline_observers_histograms_and_event_loop_metrics.mjs

import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import test from 'node:test';

test('毫秒时长仍是普通数值而不是独立运行时类型', () => {
  const seconds = 90;
  const milliseconds = seconds * 1000;

  assert.equal(milliseconds, 90_000);
  assert.equal(typeof milliseconds, 'number');
});

test('hrtime.bigint 提供高分辨率单调读数', () => {
  const first = process.hrtime.bigint();
  const second = process.hrtime.bigint();

  assert.equal(typeof first, 'bigint');
  assert.equal(second >= first, true);
});

test('performance.now 相对 timeOrigin 而不是 Unix epoch', () => {
  const first = performance.now();
  const second = performance.now();

  assert.equal(second >= first, true);
  assert.equal(performance.timeOrigin > 0, true);
});

test('Date.now 是可调整的墙上时钟', () => {
  assert.equal(Number.isInteger(Date.now()), true);

  // Date.now 可映射 Unix epoch，但系统校时可能使其跳变；经过时间优先使用单调 API。
});
