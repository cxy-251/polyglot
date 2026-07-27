// 时区跳变和日历算术边界。
// 共同问题：重复或不存在的本地时间如何映射到时间线；
// 日历字段运算与固定时长运算在时区跳变处是否等价。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/cpp/standard_library/12_time/
// polyglot-related+: test_112_calendar_day_month_year_weekday_and_indexed_components.cpp

#include <gtest/gtest.h>

#include <chrono>
#include <type_traits>

namespace {

using namespace std::chrono;

TEST(CalendarBoundaryConcept, CalendarMonthAndTimelineDaysAreDifferentOperations) {
  const year_month_day january_end = year{2024} / January / 31;
  const year_month_day calendar_candidate = january_end + months{1};
  const year_month_day timeline_result{sys_days{january_end} + days{30}};

  EXPECT_FALSE(calendar_candidate.ok());
  EXPECT_EQ(timeline_result, (year_month_day{year{2024}, March, day{1}}));
}

TEST(CalendarBoundaryConcept, LocalAndSystemTimePointsHaveDistinctDomains) {
  constexpr bool same_type = std::is_same_v<local_seconds, sys_seconds>;
  constexpr bool implicitly_convertible = std::is_convertible_v<local_seconds, sys_seconds>;
  static_assert(!same_type);
  static_assert(!implicitly_convertible);

  EXPECT_FALSE(same_type);
  EXPECT_FALSE(implicitly_convertible);

  // local_time 只有墙上字段，缺少时区就不能判定重复或不存在时间对应哪个 sys_time。
  // 锁定的 libstdc++ 11 没有 tzdb 接口，因此本实现无法安全执行 DST disambiguation。
}

}  // namespace
