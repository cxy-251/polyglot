// polyglot-covers:
// - cpp.stdlib.chrono.day-construction-ok-arithmetic-and-no-month-context
// - cpp.stdlib.chrono.month-named-constants-cyclic-arithmetic-and-ok
// - cpp.stdlib.chrono.year-range-arithmetic-and-gregorian-leap-rule
// - cpp.stdlib.chrono.calendar-literals-year-and-day
// - cpp.stdlib.chrono.weekday-sys-days-construction-and-encodings
// - cpp.stdlib.chrono.weekday-cyclic-arithmetic-and-difference
// - cpp.stdlib.chrono.weekday-indexed-valid-index-and-selection
// - cpp.stdlib.chrono.weekday-last-and-last-spec
// - cpp.stdlib.chrono.calendar-component-comparison-and-invalid-values

#include <gtest/gtest.h>

#include <chrono>
#include <compare>
#include <type_traits>

namespace {

using namespace std::chrono;
using namespace std::chrono_literals;

TEST(CalendarDay, ConstructionAndOkSeparateStorageFromCalendarValidity) {
  const day first{1};
  const day last_possible{31};
  const day zero{0};
  const day too_large{32};

  EXPECT_TRUE(first.ok());
  EXPECT_TRUE(last_possible.ok());
  EXPECT_FALSE(zero.ok());
  EXPECT_FALSE(too_large.ok());
  EXPECT_EQ(static_cast<unsigned>(last_possible), 31U);

  // day 只验证通用字段范围 [1,31]，不知道所在月份；`day{31}.ok()` 不表示“二月
  // 三十一日”有效。轻量日历类型允许先构造无效字段，再由组合类型的 ok() 检查。
}

TEST(CalendarDay, ArithmeticMovesTheFieldWithoutKnowingMonthBoundaries) {
  day value{10};
  value += days{5};
  EXPECT_EQ(value, day{15});
  value -= days{20};
  EXPECT_FALSE(value.ok());

  EXPECT_EQ(day{20} - day{5}, days{15});

  // day ± days 只是字段算术，不会借位到上个月，也不会把负结果自动变成有效日期。需要
  // 跨月移动时先构造 sys_days 再加 days。
}

TEST(CalendarMonth, NamedConstantsAndNumericConversionUseOneThroughTwelve) {
  EXPECT_EQ(January, month{1});
  EXPECT_EQ(June, month{6});
  EXPECT_EQ(December, month{12});
  EXPECT_EQ(static_cast<unsigned>(September), 9U);
  EXPECT_TRUE(December.ok());
  EXPECT_FALSE(month{0}.ok());
  EXPECT_FALSE(month{13}.ok());

  // weekday 的 C encoding 从零开始，但 month 从一开始；解析裸数字时不能共用同一偏移。
}

TEST(CalendarMonth, MonthArithmeticWrapsWithinTheTwelveMonthCycle) {
  EXPECT_EQ(December + months{1}, January);
  EXPECT_EQ(January - months{2}, November);
  EXPECT_EQ(March + months{24}, March);
  EXPECT_EQ(March - January, months{2});
  EXPECT_EQ(January - March, months{10});

  // month-month 返回向前循环到达右侧所需的非负模 12 差，不是带年份信息的时间线差。
}

TEST(CalendarYear, GregorianLeapYearsHandleCenturyExceptions) {
  EXPECT_TRUE(year{2024}.is_leap());
  EXPECT_FALSE(year{2023}.is_leap());
  EXPECT_FALSE(year{1900}.is_leap());
  EXPECT_TRUE(year{2000}.is_leap());

  // 能被 4 整除通常是闰年，能被 100 整除则不是，除非还能被 400 整除。
}

TEST(CalendarYear, ArithmeticAndRangeAreExplicit) {
  year value{2020};
  value += years{5};
  EXPECT_EQ(value, year{2025});
  EXPECT_EQ(year{2030} - year{2025}, years{5});

  EXPECT_TRUE(year::min().ok());
  EXPECT_TRUE(year::max().ok());
  EXPECT_LT(year::min(), year::max());
  EXPECT_FALSE((year::max() + years{1}).ok());

  // year 的标准有效范围是 [-32767,32767]；越界字段可表示为无效值，不能期待任意大年。
}

TEST(CalendarLiterals, SuffixesProduceStrongYearAndDayTypes) {
  constexpr auto year_value = 2024y;
  constexpr auto day_value = 29d;

  static_assert(std::is_same_v<decltype(year_value), const year>);
  static_assert(std::is_same_v<decltype(day_value), const day>);
  static_assert(year_value.is_leap());
  static_assert(day_value.ok());

  EXPECT_EQ(year_value, year{2024});
  EXPECT_EQ(day_value, day{29});

  // `d` 是 day 字面量而非 duration<days>；`29d` 是日历字段，`days{29}` 才是时长。
}

TEST(CalendarWeekday, ConstructionFromSysDaysUsesTheProlepticGregorianCalendar) {
  const sys_days known_monday = 2024y / January / 1d;
  const weekday monday{known_monday};

  EXPECT_EQ(monday, Monday);
  EXPECT_EQ(monday.c_encoding(), 1U);
  EXPECT_EQ(monday.iso_encoding(), 1U);
  EXPECT_TRUE(monday.ok());

  const weekday sunday{2024y / January / 7d};
  EXPECT_EQ(sunday, Sunday);
  EXPECT_EQ(sunday.c_encoding(), 0U);
  EXPECT_EQ(sunday.iso_encoding(), 7U);

  // c_encoding 采用 Sunday=0，ISO 采用 Monday=1、Sunday=7；持久化星期编号前必须声明
  // 采用哪一种编码。
}

TEST(CalendarWeekday, ArithmeticWrapsThroughASevenDayCycle) {
  EXPECT_EQ(Monday + days{3}, Thursday);
  EXPECT_EQ(Sunday - days{1}, Saturday);
  EXPECT_EQ(Thursday - Monday, days{3});
  EXPECT_EQ(Monday - Thursday, days{4});
  EXPECT_EQ(Monday + days{14}, Monday);

  // weekday-weekday 和 month-month 类似，给出模周期的前向差，不产生负三天。
}

TEST(CalendarWeekday, NumericConstructionNormalizesSevenToSunday) {
  EXPECT_EQ(weekday{0}, Sunday);
  EXPECT_EQ(weekday{7}, Sunday);
  EXPECT_TRUE(weekday{7}.ok());
  EXPECT_FALSE(weekday{8}.ok());

  // 标准特意让 7 也表示 Sunday，便于 ISO 编码转换；8–255 仍是无效 weekday。
}

TEST(WeekdayIndexed, IndexOneThroughFiveDescribesNthOccurrence) {
  const weekday_indexed second_monday = Monday[2];
  const weekday_indexed fifth_friday{Friday, 5};
  const weekday_indexed invalid = Tuesday[0];

  EXPECT_EQ(second_monday.weekday(), Monday);
  EXPECT_EQ(second_monday.index(), 2U);
  EXPECT_TRUE(second_monday.ok());
  EXPECT_TRUE(fifth_friday.ok());
  EXPECT_FALSE(invalid.ok());

  // index 的结构有效范围是 1–5；“这个月是否真的有第五个星期五”还需要与年月组合后
  // 检查 year_month_weekday::ok()。
}

TEST(WeekdayLast, ItRepresentsTheLastOccurrenceWithoutGuessingAnIndex) {
  const weekday_last last_friday = Friday[last];

  EXPECT_EQ(last_friday.weekday(), Friday);
  EXPECT_TRUE(last_friday.ok());
  static_assert(std::is_same_v<decltype(last), const last_spec>);

  // 最后一个星期几不一定是第四次或第五次出现；weekday_last 直接表达意图，避免先猜
  // index 再回退。
}

template <class T>
concept LessThanOrdered = requires(T left, T right) {
  left < right;
};

TEST(CalendarComponents, LinearFieldsAreOrderedButCyclicWeekdayIsNot) {
  EXPECT_LT(day{3}, day{10});
  EXPECT_LT(March, December);
  EXPECT_LT(year{1999}, year{2000});
  EXPECT_EQ(Monday, weekday{1});
  static_assert(!LessThanOrdered<weekday>);

  // day/month/year 的比较只比较字段值；weekday 是循环而没有自然的小于关系，只提供
  // 相等和模七差。完整日期的时间线顺序应比较 year_month_day 或 sys_days。
}

}  // namespace
