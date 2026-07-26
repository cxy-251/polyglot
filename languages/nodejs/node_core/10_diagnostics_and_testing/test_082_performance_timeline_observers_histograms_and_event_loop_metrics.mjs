// polyglot-covers:
// - nodejs.core.perf-hooks-monotonic-clock-time-origin-and-node-timing
// - nodejs.core.perf-hooks-mark-measure-detail-query-and-clear
// - nodejs.core.perf-hooks-resource-timing-and-buffer
// - nodejs.core.perf-hooks-performance-observer-delivery-filter-and-disconnect
// - nodejs.core.perf-hooks-timerify-sync-async-and-arguments
// - nodejs.core.perf-hooks-recordable-histogram-record-add-percentiles-and-reset
// - nodejs.core.perf-hooks-event-loop-utilization-snapshots
// - nodejs.core.perf-hooks-event-loop-delay-monitor-lifecycle-and-units

import assert from 'node:assert/strict';
import {
  createHistogram,
  eventLoopUtilization,
  monitorEventLoopDelay,
  performance,
  PerformanceObserver,
  timerify,
} from 'node:perf_hooks';
import { setImmediate } from 'node:timers/promises';
import test from 'node:test';

test.afterEach(() => {
  performance.clearMarks();
  performance.clearMeasures();
  performance.clearResourceTimings();
});

test('performance.now 是进程起点后的单调毫秒时间，timeOrigin 才是 Unix 时间', () => {
  const first = performance.now();
  const second = performance.now();
  assert.ok(second >= first);
  assert.ok(performance.timeOrigin > 0);
  assert.ok(Math.abs(performance.timeOrigin + second - Date.now()) < 2_000);

  const timing = performance.nodeTiming;
  assert.equal(timing.entryType, 'node');
  assert.equal(timing.name, 'node');
  assert.equal(timing.startTime, 0);
  assert.ok(timing.nodeStart >= 0);
  assert.ok(timing.v8Start >= timing.nodeStart);
  assert.ok(timing.bootstrapComplete >= timing.v8Start);

  const json = performance.toJSON();
  assert.equal(json.timeOrigin, performance.timeOrigin);
  assert.equal(json.nodeTiming.name, 'node');
  // now 不能与 Date.now 直接比较；二者相加 timeOrigin 后才落在相同的 Unix 时间轴上。
});

test('mark/measure 可用显式时间构造确定区间，并保存结构化 detail', () => {
  const start = performance.mark('compile:start', {
    startTime: 10,
    detail: { files: 3 },
  });
  const end = performance.mark('compile:end', { startTime: 25 });
  const measure = performance.measure('compile', {
    start: 'compile:start',
    end: 'compile:end',
    detail: { cache: 'cold' },
  });

  assert.equal(start.entryType, 'mark');
  assert.equal(start.duration, 0);
  assert.deepEqual(start.detail, { files: 3 });
  assert.equal(end.startTime, 25);
  assert.equal(measure.startTime, 10);
  assert.equal(measure.duration, 15);
  assert.deepEqual(measure.detail, { cache: 'cold' });
  assert.equal(performance.getEntriesByName('compile', 'measure')[0], measure);
  assert.deepEqual(
    performance.getEntriesByType('mark').map(({ name }) => name),
    ['compile:start', 'compile:end'],
  );

  performance.clearMarks('compile:start');
  assert.deepEqual(performance.getEntriesByName('compile:start'), []);
  assert.throws(
    () => performance.measure('missing-range', 'compile:start', 'compile:end'),
    { name: 'SyntaxError' },
  );
  // 时间线是进程级可变状态；读取后必须 clear，测试和长期运行服务尤其不能无限积累。
});

test('performance 方法需要正确 receiver，解构后裸调用不是普通工具函数', () => {
  const detachedNow = performance.now;
  const detachedMark = performance.mark;
  assert.throws(() => detachedNow(), TypeError);
  assert.throws(() => detachedMark('detached'), TypeError);
  assert.equal(Reflect.apply(detachedNow, performance, []) >= 0, true);
});

test('markResourceTiming 建立资源条目，并将响应元数据放到标准字段', () => {
  const timingInfo = {
    startTime: 10,
    redirectStartTime: 0,
    redirectEndTime: 0,
    postRedirectStartTime: 10,
    finalServiceWorkerStartTime: 0,
    finalNetworkRequestStartTime: 12,
    finalNetworkResponseStartTime: 16,
    endTime: 20,
    finalConnectionTimingInfo: null,
    encodedBodySize: 7,
    decodedBodySize: 11,
  };
  const resource = performance.markResourceTiming(
    timingInfo,
    'https://example.test/data.json',
    'fetch',
    globalThis,
    '',
    { encodedBodySize: 7, decodedBodySize: 11 },
    200,
    'cache',
  );

  assert.equal(resource.entryType, 'resource');
  assert.equal(resource.name, 'https://example.test/data.json');
  assert.equal(resource.initiatorType, 'fetch');
  assert.equal(resource.startTime, 10);
  assert.equal(resource.duration, 10);
  assert.equal(resource.responseStatus, 200);
  assert.equal(resource.deliveryType, 'cache');
  assert.equal(resource.encodedBodySize, 7);
  assert.equal(resource.decodedBodySize, 11);
  assert.equal(performance.getEntriesByType('resource')[0], resource);

  performance.clearResourceTimings(resource.name);
  assert.deepEqual(performance.getEntriesByType('resource'), []);
  // 这只是记录已有 fetch 阶段，不会发起请求；cacheMode 只允许空字符串或 local。
});

test('PerformanceObserver 异步批量投递，并可在 EntryList 中再次筛选', async () => {
  assert.ok(PerformanceObserver.supportedEntryTypes.includes('mark'));
  assert.ok(PerformanceObserver.supportedEntryTypes.includes('measure'));

  let callbackObserver;
  const delivered = new Promise((resolve) => {
    const observer = new PerformanceObserver((list, currentObserver) => {
      callbackObserver = currentObserver;
      resolve({
        all: list.getEntries(),
        marks: list.getEntriesByType('mark'),
        named: list.getEntriesByName('observer:measure', 'measure'),
      });
    });
    observer.observe({ entryTypes: ['mark', 'measure'] });
    performance.mark('observer:start', { startTime: 30 });
    performance.mark('observer:end', { startTime: 34 });
    performance.measure('observer:measure', 'observer:start', 'observer:end');
  });

  const entries = await delivered;
  assert.deepEqual(
    entries.all.map(({ entryType }) => entryType),
    ['mark', 'measure', 'mark'],
  );
  assert.deepEqual(
    entries.marks.map(({ name }) => name),
    ['observer:start', 'observer:end'],
  );
  assert.equal(entries.named[0].duration, 4);
  callbackObserver.disconnect();

  performance.mark('observer:after-disconnect');
  await setImmediate();
  assert.deepEqual(callbackObserver.takeRecords(), []);
  // Observer 本身有开销；使用完 disconnect，clearMarks/clearMeasures 是另一项独立清理。
});

test('timerify 保持调用语义，并在同步返回或异步落定后记录 function 条目', async () => {
  const histogram = createHistogram();
  const entries = [];
  const observer = new PerformanceObserver((list) => entries.push(...list.getEntries()));
  observer.observe({ type: 'function' });

  const receiver = { factor: 6 };
  const multiply = timerify(function multiply(value) {
    assert.equal(this, receiver);
    return this.factor * value;
  }, { histogram });
  const asyncIdentity = timerify(async function asyncIdentity(value) {
    await Promise.resolve();
    return value;
  }, { histogram });

  assert.equal(multiply.call(receiver, 7), 42);
  assert.equal(await asyncIdentity('ready'), 'ready');
  await setImmediate();
  observer.disconnect();

  assert.deepEqual(entries.map(({ name }) => name), ['multiply', 'asyncIdentity']);
  assert.deepEqual(entries[0].detail, [7]);
  assert.deepEqual(entries[1].detail, ['ready']);
  assert.ok(entries.every(({ duration }) => duration >= 0));
  assert.equal(histogram.count, 2);
  // 异步函数测到的是 Promise 落定前的完整时长，而不是仅测创建 Promise 的同步部分。
});

test('RecordableHistogram 汇总整数/BigInt、合并分布、查询百分位并重置', () => {
  const histogram = createHistogram({ lowest: 1, highest: 1_000, figures: 3 });
  histogram.record(10);
  histogram.record(20n);
  const other = createHistogram({ lowest: 1, highest: 1_000, figures: 3 });
  other.record(30);
  histogram.add(other);

  assert.equal(histogram.count, 3);
  assert.equal(histogram.countBigInt, 3n);
  assert.equal(histogram.min, 10);
  assert.equal(histogram.max, 30);
  assert.equal(histogram.percentile(50), 20);
  assert.equal(histogram.percentileBigInt(100), 30n);
  assert.ok(histogram.percentiles instanceof Map);
  assert.equal(histogram.exceeds, 0);

  histogram.reset();
  assert.equal(histogram.count, 0);
  assert.equal(histogram.minBigInt, 9_223_372_036_854_775_807n);
  assert.equal(histogram.max, 0);
  // HDR Histogram 会按 figures 控制精度；不要把生产延迟统计误当成保存每个原始样本。
});

test('eventLoopUtilization 用前后快照求差值，字段是毫秒和比例而非 CPU 百分数', async () => {
  const before = eventLoopUtilization();
  await setImmediate();
  const after = eventLoopUtilization();
  const delta = performance.eventLoopUtilization(after, before);

  assert.ok(delta.idle >= 0);
  assert.ok(delta.active >= 0);
  assert.ok(Number.isFinite(delta.utilization));
  assert.ok(delta.utilization >= 0 && delta.utilization <= 1);
  assert.notEqual(after, before);
  // 同步阻塞仍计入 active；它不是操作系统 CPU 使用率，也不能传入自行伪造的快照对象。
});

test('monitorEventLoopDelay 显式启停采样器，直方图的延迟单位是纳秒', () => {
  const histogram = monitorEventLoopDelay({ resolution: 10 });
  assert.equal(histogram.enable(), true);
  assert.equal(histogram.enable(), false);
  assert.equal(histogram.disable(), true);
  assert.equal(histogram.disable(), false);
  assert.equal(histogram.count, 0);
  histogram.reset();

  histogram.enable();
  histogram[Symbol.dispose]();
  assert.equal(histogram.disable(), false);
  // resolution 用毫秒配置采样频率，但 min/max/mean/percentile 的观测值统一是纳秒。
});
