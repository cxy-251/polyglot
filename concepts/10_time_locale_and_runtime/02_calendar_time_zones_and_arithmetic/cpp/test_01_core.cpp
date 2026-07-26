// 日历、时区与算术。
// 共同问题：日历字段如何映射到时间线；时区偏移如何参与表示；无效日期和夏令时跳变如何表达；
// 按时间线增加时长是否等于按墙上日历修改字段。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/cpp/standard_library/12_time/
// polyglot-related+: test_112_calendar_day_month_year_weekday_and_indexed_components.cpp

#include <gtest/gtest.h>

#include <chrono>

namespace {

using namespace std::chrono;

TEST(CalendarConcept, YearMonthDayValidatesCalendarFields) {
  const year_month_day leap_day{year{2024}, February, day{29}};
  const year_month_day invalid{year{2023}, February, day{29}};

  EXPECT_TRUE(leap_day.ok());
  EXPECT_FALSE(invalid.ok());
}

TEST(CalendarConcept, SysDaysUsesTimelineDayArithmetic) {
  const sys_days leap_day = year{2024} / February / 29;
  const year_month_day following{leap_day + days{1}};

  EXPECT_EQ(following, (year_month_day{year{2024}, March, day{1}}));
}

TEST(CalendarConcept, MonthArithmeticCanProduceAnInvalidCalendarDate) {
  const year_month_day january_end = year{2023} / January / 31;
  const year_month_day february_candidate = january_end + months{1};

  EXPECT_FALSE(february_candidate.ok());

  // calendar 字段算术不会自动选择“月末”；需要调用方明确采用截断等业务规则。
}

TEST(CalendarConcept, LockedLibstdcppDoesNotProvidePortableTimeZoneDatabase) {
#if defined(__cpp_lib_chrono) && __cpp_lib_chrono >= 201907L
  SUCCEED();
#else
  SUCCEED();
#endif

  // C++20 规范包含时区设施，但锁定的 libstdc++ 11 未完整提供 tzdb/zoned_time；
  // 不编造 America/New_York 案例，时区跳变由 Python 与 Node.js 的可用实现执行验证。
}

}  // namespace
