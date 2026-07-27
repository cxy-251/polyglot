// 时长单位和时钟边界。
// 共同问题：时长是否携带单位；墙上时间回拨时经过时间如何计算；
// 数值精度与单位转换由调用方还是类型系统约束。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/nodejs/node_core/10_diagnostics_and_testing/
// polyglot-related+: test_082_performance_timeline_observers_histograms_and_event_loop_metrics.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function elapsed(start, finish) {
  return finish - start;
}

test('普通数值不携带时长单位，调用方必须显式换算', () => {
  const seconds = 1;
  const milliseconds = 250;

  assert.equal(seconds + milliseconds, 251);
  assert.equal(seconds * 1_000 + milliseconds, 1_250);
});

test('BigInt 纳秒保留整数精度但不能与 Number 隐式混算', () => {
  const duration = 1_000_000_001n;

  assert.equal(duration / 1_000_000n, 1_000n);
  assert.throws(() => duration + 1, TypeError);
});

test('单调读数在墙上时钟回拨样本中仍表达正向经过时间', () => {
  const wallSamples = [1_000, 995];
  const monotonicSamples = [40, 42.5];

  assert.equal(elapsed(...wallSamples), -5);
  assert.equal(elapsed(...monotonicSamples), 2.5);

  // 注入读数避免修改主机时钟；真实测量应从 performance.now 或 hrtime.bigint 取得单调样本。
});
