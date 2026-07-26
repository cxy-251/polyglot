// polyglot-covers:
// - cpp.stdlib.chrono.tzdb-list-current-locate-and-version
// - cpp.stdlib.chrono.time-zone-sys-info-local-info-and-conversions
// - cpp.stdlib.chrono.nonexistent-local-time-exception-and-choose-policy
// - cpp.stdlib.chrono.ambiguous-local-time-exception-and-choose-policy
// - cpp.stdlib.chrono.zoned-time-construction-observers-and-utc-workflow
// - cpp.stdlib.chrono.leap-second-info-links-and-remote-database-boundary
// - cpp.stdlib.chrono.format-duration-calendar-sys-time-and-zone-fields
// - cpp.stdlib.chrono.from-stream-date-time-duration-and-parse-failure
// - cpp.stdlib.chrono.time-zone-and-formatting-feature-detection

#include <gtest/gtest.h>

#include <chrono>
#include <sstream>
#include <string>

#if __has_include(<format>)
#include <format>
#define POLYGLOT_HAS_STD_FORMAT_HEADER 1
#else
#define POLYGLOT_HAS_STD_FORMAT_HEADER 0
#endif

namespace {

using namespace std::chrono;
using namespace std::chrono_literals;

#if defined(__cpp_lib_chrono) && __cpp_lib_chrono >= 201907L

TEST(TimeZoneDatabase, LocateZoneReturnsAStablePointerOwnedByTheDatabase) {
  const tzdb& database = get_tzdb();
  const time_zone* first = locate_zone("UTC");
  const time_zone* second = database.locate_zone("UTC");

  ASSERT_NE(first, nullptr);
  EXPECT_EQ(first, second);
  EXPECT_FALSE(database.version.empty());

  // time_zone 指针由 tzdb_list 拥有，在删除对应 tzdb 前保持有效。不要 delete，也不要在
  // reload_tzdb 后无限期缓存旧版本规则却假定它是最新规则。
}

TEST(TimeZoneConversion, UtcMapsSysAndLocalTimeWithZeroOffset) {
  const time_zone* utc = locate_zone("UTC");
  const sys_seconds system_point =
      sys_days{2024y / February / 29d} + 12h + 34min + 56s;
  const local_seconds local_point = utc->to_local(system_point);
  const sys_seconds round_trip = utc->to_sys(local_point);
  const sys_info information = utc->get_info(system_point);

  EXPECT_EQ(local_point.time_since_epoch(), system_point.time_since_epoch());
  EXPECT_EQ(round_trip, system_point);
  EXPECT_EQ(information.offset, 0s);
  EXPECT_EQ(information.save, 0min);

  // UTC 是确定性零偏移示例；其他时区的 offset/save/abbrev 都随历史区间变化，不能缓存
  // 一个“当前偏移”来转换任意日期。
}

TEST(LocalTimeConversion, SpringForwardGapThrowsUnlessAChoosePolicyIsGiven) {
  const time_zone* new_york = locate_zone("America/New_York");
  const local_seconds missing =
      local_days{2021y / March / 14d} + 2h + 30min;
  const local_info information = new_york->get_info(missing);

  EXPECT_EQ(information.result, local_info::nonexistent);
  EXPECT_THROW(static_cast<void>(new_york->to_sys(missing)),
               nonexistent_local_time);

  const sys_seconds earliest = new_york->to_sys(missing, choose::earliest);
  const sys_seconds latest = new_york->to_sys(missing, choose::latest);
  EXPECT_EQ(earliest, latest);

  // 春季跳时产生不存在的本地区间；无策略转换抛异常。对 gap，earliest/latest 都映射到
  // 跳变边界，而不是凭空保留 02:30。
}

TEST(LocalTimeConversion, FallBackOverlapHasTwoPossibleSystemTimes) {
  const time_zone* new_york = locate_zone("America/New_York");
  const local_seconds repeated =
      local_days{2021y / November / 7d} + 1h + 30min;
  const local_info information = new_york->get_info(repeated);

  EXPECT_EQ(information.result, local_info::ambiguous);
  EXPECT_THROW(static_cast<void>(new_york->to_sys(repeated)),
               ambiguous_local_time);

  const sys_seconds earliest = new_york->to_sys(repeated, choose::earliest);
  const sys_seconds latest = new_york->to_sys(repeated, choose::latest);
  EXPECT_EQ(latest - earliest, 1h);

  // 秋季回拨让同一墙上读数出现两次；业务必须保存 offset/zone 或显式 earliest/latest，
  // 不能只保存无时区的 local_time 后猜测。
}

TEST(ZonedTime, ItKeepsAZonePointerBesideAnAbsoluteTimePoint) {
  const time_zone* utc = locate_zone("UTC");
  const sys_seconds system_point = sys_days{2030y / January / 2d} + 3h;
  const zoned_time<seconds> zoned{utc, system_point};

  EXPECT_EQ(zoned.get_time_zone(), utc);
  EXPECT_EQ(zoned.get_sys_time(), system_point);
  EXPECT_EQ(zoned.get_local_time().time_since_epoch(),
            system_point.time_since_epoch());
  EXPECT_EQ(zoned.get_info().offset, 0s);

  // zoned_time 不把时区规则复制进对象；它组合 time_zone 指针和 sys_time，并按数据库
  // 规则即时得到 local_time。
}

TEST(LeapSeconds, DatabaseOwnsVersionedLeapAndLinkRecords) {
  const tzdb& database = get_tzdb();

  EXPECT_GE(database.zones.size(), 1U);
  RecordProperty("tzdb_link_count", database.links.size());
  RecordProperty("tzdb_leap_second_count", database.leap_seconds.size());

  // links 和 leap_seconds 的具体数量属于数据库版本数据，不写死。remote_version 与
  // reload_tzdb 可能访问外部资源或改变全局 tzdb_list，本测试只记录边界而不调用。
}

#else

TEST(TimeZones, LockedLibstdcxxGapPreservesTheCompleteUpgradePath) {
  GTEST_SKIP()
      << "GCC 11 libstdc++ 的 __cpp_lib_chrono 早于 201907L；tzdb、time_zone、"
      << "zoned_time、DST 异常和 leap-second 案例已保留在特性分支";
}

#endif

#if POLYGLOT_HAS_STD_FORMAT_HEADER && defined(__cpp_lib_format) && \
    __cpp_lib_format >= 201907L && defined(__cpp_lib_chrono) && \
    __cpp_lib_chrono >= 201907L

TEST(ChronoFormatting, FormatHandlesDurationsCalendarsAndSystemTimeFields) {
  const sys_seconds point =
      sys_days{2024y / February / 29d} + 12h + 34min + 56s;

  EXPECT_EQ(std::format("{:%Q%q}", 1500ms), "1500ms");
  EXPECT_EQ(std::format("{:%F}", 2024y / February / 29d), "2024-02-29");
  EXPECT_EQ(std::format("{:%F %T}", point), "2024-02-29 12:34:56");

  // %Q 是 duration count，%q 是单位后缀；%F 等于 %Y-%m-%d，%T 等于 %H:%M:%S。
  // chrono 格式说明位于 format replacement field 内，和 strftime 的 C 缓冲区 API 不同。
}

TEST(ChronoFormatting, ZonedTimeAddsOffsetAndAbbreviationFields) {
  const zoned_seconds zoned{
      "UTC", sys_days{2024y / January / 1d} + 1h};
  const std::string rendered = std::format("{:%F %T %Z %z}", zoned);

  EXPECT_NE(rendered.find("2024-01-01 01:00:00"), std::string::npos);
  EXPECT_NE(rendered.find("+0000"), std::string::npos);

  // %Z 来自时区缩写，文本可能由数据库决定；%z 是数值偏移，更适合机器协议但仍应
  // 同时保存 zone ID 才能重算未来规则。
}

TEST(ChronoParsing, FromStreamBuildsATypedTimePointAndReportsFailureInTheStream) {
  std::istringstream valid{"2024-02-29 12:34:56"};
  sys_seconds point;
  from_stream(valid, "%F %T", point);

  ASSERT_TRUE(valid);
  EXPECT_EQ(point,
            sys_days{2024y / February / 29d} + 12h + 34min + 56s);

  std::istringstream invalid{"2024-02-30"};
  sys_days bad_point;
  from_stream(invalid, "%F", bad_point);
  EXPECT_TRUE(invalid.fail());

  // 解析失败通过 failbit 报告；不要在检查流状态之前使用目标值。
}

TEST(ChronoParsing, DurationParsingCanCaptureAbbreviationAndOffsetSeparately) {
  std::istringstream input{"01:02:03 +0530 IST"};
  seconds elapsed{};
  minutes offset{};
  std::string abbreviation;
  from_stream(input, "%T %z %Z", elapsed, &abbreviation, &offset);

  ASSERT_TRUE(input);
  EXPECT_EQ(elapsed, 1h + 2min + 3s);
  EXPECT_EQ(offset, 330min);
  EXPECT_EQ(abbreviation, "IST");
}

#else

TEST(ChronoFormattingAndParsing, LockedToolchainGapIsExplicit) {
  GTEST_SKIP()
      << "锁定 GCC 11/libstdc++ 缺少完整 <format> 与 C++20 chrono I/O；"
      << "duration/calendar/zoned formatting 和 from_stream 案例已保留";
}

#endif

}  // namespace

#undef POLYGLOT_HAS_STD_FORMAT_HEADER
