// 时区跳变和日历算术边界。
// 共同问题：重复或不存在的本地时间如何映射到时间线；
// 日历字段运算与固定时长运算在时区跳变处是否等价。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/nodejs/language/
// polyglot-related+: test_022_date_epoch_parsing_calendar_arithmetic_and_time_zones.mjs

import assert from 'node:assert/strict';
import test from 'node:test';

function localTime(instant) {
  return new Intl.DateTimeFormat('en-CA', {
    hour: '2-digit',
    hourCycle: 'h23',
    minute: '2-digit',
    timeZone: 'America/New_York',
  }).format(instant);
}

test('两个时间线瞬间可以格式化为同一个重复本地时间', () => {
  const daylight = new Date('2021-11-07T05:30:00Z');
  const standard = new Date('2021-11-07T06:30:00Z');

  assert.equal(localTime(daylight), '01:30');
  assert.equal(localTime(standard), '01:30');
  assert.equal(standard - daylight, 60 * 60 * 1000);

  // Date 只保存时间值；仅有格式化后的 01:30 无法反推出两个瞬间中的哪一个。
});

test('时间线跨越春季跳变时不存在的本地小时不会出现', () => {
  const before = new Date('2021-03-14T06:30:00Z');
  const after = new Date(before.getTime() + 60 * 60 * 1000);

  assert.equal(localTime(before), '01:30');
  assert.equal(localTime(after), '03:30');
});

test('修改日历月份与增加固定天数不是同一种运算', () => {
  const calendar = new Date('2024-01-31T00:00:00Z');
  const timeline = new Date(calendar.getTime() + 30 * 24 * 60 * 60 * 1000);

  calendar.setUTCMonth(calendar.getUTCMonth() + 1);

  assert.equal(calendar.toISOString(), '2024-03-02T00:00:00.000Z');
  assert.equal(timeline.toISOString(), '2024-03-01T00:00:00.000Z');
});
