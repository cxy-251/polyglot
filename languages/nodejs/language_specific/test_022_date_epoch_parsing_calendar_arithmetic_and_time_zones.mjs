// polyglot-covers:
// - nodejs.language.date-epoch-and-time-value
// - nodejs.language.date-iso-parsing-and-construction
// - nodejs.language.date-local-versus-utc
// - nodejs.language.date-calendar-overflow
// - nodejs.language.date-arithmetic-and-comparison
// - nodejs.language.invalid-date-and-time-clip
// - nodejs.language.date-json-and-iso-formatting

import assert from 'node:assert/strict';
import test from 'node:test';

test('Date 内部时间值是自 Unix epoch 起的毫秒数', () => {
  const epoch = new Date(0);
  const nextSecond = new Date(1000);

  assert.equal(epoch.valueOf(), 0);
  assert.equal(epoch.getTime(), 0);
  assert.equal(epoch.toISOString(), '1970-01-01T00:00:00.000Z');
  assert.equal(nextSecond.toISOString(), '1970-01-01T00:00:01.000Z');
  assert.equal(Number(nextSecond), 1000);
});

test('ISO 字符串中的 Z 与显式 offset 表示绝对时刻', () => {
  const utc = new Date('2026-07-22T12:00:00.000Z');
  const offset = new Date('2026-07-22T20:00:00.000+08:00');

  assert.equal(utc.getTime(), offset.getTime());
  assert.equal(offset.toISOString(), '2026-07-22T12:00:00.000Z');

  const dateOnly = new Date('2026-07-22');
  assert.equal(dateOnly.toISOString(), '2026-07-22T00:00:00.000Z');
});

test('无 offset 的日期时间按本地时区解释，日期单独字符串按 UTC', () => {
  const local = new Date('2026-07-22T00:00:00');
  const utc = new Date('2026-07-22T00:00:00Z');

  const expectedDifference = local.getTimezoneOffset() * 60_000;
  assert.equal(local.getTime() - utc.getTime(), expectedDifference);

  // 同一种 ISO 外观会因是否包含时间部分而改变默认时区，跨系统数据应始终携带 Z/offset。
});

test('多参数构造使用本地时间且月份从零开始', () => {
  const local = new Date(2026, 0, 2, 3, 4, 5, 6);

  assert.equal(local.getFullYear(), 2026);
  assert.equal(local.getMonth(), 0);
  assert.equal(local.getDate(), 2);
  assert.equal(local.getHours(), 3);

  const utcMilliseconds = Date.UTC(2026, 0, 2, 3, 4, 5, 6);
  assert.equal(
    new Date(utcMilliseconds).toISOString(),
    '2026-01-02T03:04:05.006Z',
  );
});

test('构造器和 setter 会规范化超出范围的日历字段', () => {
  assert.equal(
    new Date(Date.UTC(2026, 12, 1)).toISOString(),
    '2027-01-01T00:00:00.000Z',
  );
  assert.equal(
    new Date(Date.UTC(2026, 1, 0)).toISOString(),
    '2026-01-31T00:00:00.000Z',
  );

  const date = new Date('2026-01-31T00:00:00.000Z');
  date.setUTCMonth(1);
  assert.equal(date.toISOString(), '2026-03-03T00:00:00.000Z');

  // “给 1 月 31 日加一个月”不是稳定的业务定义；先明确月底截断等规则再实现。
});

test('UTC getter/setter 避免测试依赖宿主机时区', () => {
  const date = new Date('2026-07-22T12:34:56.789Z');

  assert.deepEqual({
    date: date.getUTCDate(),
    hours: date.getUTCHours(),
    milliseconds: date.getUTCMilliseconds(),
    month: date.getUTCMonth(),
    year: date.getUTCFullYear(),
  }, {
    date: 22,
    hours: 12,
    milliseconds: 789,
    month: 6,
    year: 2026,
  });

  date.setUTCDate(23);
  date.setUTCHours(0, 0, 0, 0);
  assert.equal(date.toISOString(), '2026-07-23T00:00:00.000Z');
});

test('Date 相减得到毫秒差，其他比较会转成时间值', () => {
  const start = new Date('2026-07-22T00:00:00.000Z');
  const end = new Date('2026-07-22T01:30:00.000Z');

  assert.equal(end - start, 90 * 60 * 1000);
  assert.equal(end > start, true);
  assert.equal(+start, start.getTime());

  // Date 加法会偏向字符串拼接，因为 Date 的默认 primitive hint 是 string。
  assert.equal(typeof (start + 1000), 'string');
  assert.equal(new Date(start.getTime() + 1000).toISOString(), '2026-07-22T00:00:01.000Z');
});

test('非法日期保存 NaN，部分格式化方法才抛 RangeError', () => {
  const invalid = new Date('not a date');

  assert.equal(Number.isNaN(invalid.getTime()), true);
  assert.equal(invalid.toString(), 'Invalid Date');
  assert.throws(() => invalid.toISOString(), RangeError);
  assert.equal(invalid.toJSON(), null);
  assert.equal(JSON.stringify({ invalid }), '{"invalid":null}');
});

test('TimeClip 限制 Date 可表示范围约为 epoch 前后 1 亿天', () => {
  const maximum = 8.64e15;
  assert.equal(new Date(maximum).toISOString(), '+275760-09-13T00:00:00.000Z');
  assert.equal(Number.isNaN(new Date(maximum + 1).getTime()), true);
  assert.equal(new Date(-maximum).toISOString(), '-271821-04-20T00:00:00.000Z');
});

test('Date.parse 对规范 ISO 格式可靠，其他自然语言格式不应跨环境依赖', () => {
  assert.equal(
    Date.parse('2026-07-22T12:00:00.000Z'),
    Date.UTC(2026, 6, 22, 12),
  );
  assert.equal(Number.isNaN(Date.parse('definitely not a date')), true);

  // 规范只强制支持简化 ISO、toString 和 toUTCString 等格式；用户输入应由明确解析器验证。
});
