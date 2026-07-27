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

#if defined(__cpp_lib_chrono) && __cpp_lib_chrono >= 201907L
constexpr bool kChronoFeatureMacroHasTimeZones = true;
constexpr bool kChronoInterfacesAreAvailable =
    requires {
      std::chrono::get_tzdb();
      typename std::chrono::zoned_time<std::chrono::seconds>;
    };
#else
constexpr bool kChronoFeatureMacroHasTimeZones = false;
constexpr bool kChronoInterfacesAreAvailable = false;
#endif

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

TEST(CalendarConcept, FeatureMacroAndTimeZoneInterfacesAgree) {
#if defined(__cpp_lib_chrono) && __cpp_lib_chrono >= 201907L
  static_assert(kChronoInterfacesAreAvailable);
  const time_zone* utc = locate_zone("UTC");
  ASSERT_NE(utc, nullptr);
  EXPECT_EQ(utc->get_info(sys_seconds{}).offset, seconds{0});
#else
  static_assert(!kChronoInterfacesAreAvailable);
  EXPECT_FALSE(kChronoFeatureMacroHasTimeZones);
#endif

  EXPECT_EQ(kChronoFeatureMacroHasTimeZones, kChronoInterfacesAreAvailable);

  // 标准版本与库实现能力是两件事。锁定的 libstdc++ 11 未声明 201907L，因此不能引用
  // tzdb/zoned_time；支持该宏的实现则必须编译并执行上面的 UTC 接口案例。
}

}  // namespace
