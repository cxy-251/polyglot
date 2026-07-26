// 日历、时区与算术。
// 共同问题：日历字段如何映射到时间线；时区偏移如何参与表示；无效日期和夏令时跳变如何表达；
// 按时间线增加时长是否等于按墙上日历修改字段。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/nodejs/language/
// polyglot-related+: test_022_date_epoch_parsing_calendar_arithmetic_and_time_zones.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function localHour(instant, timeZone) {
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    hourCycle: 'h23',
    timeZone,
  }).format(instant);
}

test('Date 的 epoch 毫秒表示唯一时间线瞬间', () => {
  const instant = new Date('2024-01-01T00:00:00.000Z');

  assert.equal(instant.getTime(), 1_704_067_200_000);
  assert.equal(instant.toISOString(), '2024-01-01T00:00:00.000Z');
});

test('Date 构造器规范化越界日历字段', () => {
  const normalized = new Date(Date.UTC(2023, 1, 29));

  assert.equal(normalized.toISOString(), '2023-03-01T00:00:00.000Z');

  // 这与 Python 抛 ValueError、C++ year_month_day 保留 invalid 状态均不相同。
});

test('同一时间线小时可跨过不存在的本地小时', () => {
  const before = new Date('2021-03-14T06:30:00Z');
  const after = new Date(before.getTime() + 60 * 60 * 1000);

  assert.equal(localHour(before, 'America/New_York'), '01');
  assert.equal(localHour(after, 'America/New_York'), '03');
});

test('Intl 显式时区不依赖宿主默认时区', () => {
  const instant = new Date('2024-01-01T00:00:00Z');

  assert.equal(localHour(instant, 'UTC'), '00');
  assert.equal(localHour(instant, 'Asia/Shanghai'), '08');
});
