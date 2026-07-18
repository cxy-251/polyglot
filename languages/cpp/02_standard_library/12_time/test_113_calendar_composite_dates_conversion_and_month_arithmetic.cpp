// polyglot-covers:
// - cpp.stdlib.chrono.month-day-and-month-day-last-validity
// - cpp.stdlib.chrono.month-weekday-and-month-weekday-last-selection
// - cpp.stdlib.chrono.year-month-field-arithmetic-and-rollover
// - cpp.stdlib.chrono.year-month-day-validity-getters-and-ordering
// - cpp.stdlib.chrono.year-month-day-sys-days-and-local-days-round-trip
// - cpp.stdlib.chrono.invalid-year-month-day-normalizes-when-converted
// - cpp.stdlib.chrono.calendar-month-and-year-arithmetic-does-not-clamp-day
// - cpp.stdlib.chrono.year-month-day-last-leap-aware-last-day
// - cpp.stdlib.chrono.year-month-weekday-indexed-conversion-and-validity
// - cpp.stdlib.chrono.year-month-weekday-last-conversion
// - cpp.stdlib.chrono.calendar-conventional-slash-syntax
// - cpp.stdlib.chrono.months-years-average-duration-versus-calendar-fields

#include <gtest/gtest.h>

#include <chrono>
#include <ratio>
#include <type_traits>

namespace {

using namespace std::chrono;
using namespace std::chrono_literals;

TEST(MonthDay, ItChecksWhetherTheCombinationCanExistInSomeYear) {
  const month_day leap_birthday = February / 29d;
  const month_day impossible = April / 31d;

  EXPECT_EQ(leap_birthday.month(), February);
  EXPECT_EQ(leap_birthday.day(), day{29});
  EXPECT_TRUE(leap_birthday.ok());
  EXPECT_FALSE(impossible.ok());

  // month_day 没有年份，2 月 29 日只要在某个闰年能存在就算 ok；与具体年份组合后还要
  // 由 year_month_day 再检查一次。
}

TEST(MonthDayLast, ItDefersTheActualDayUntilAYearIsKnown) {
  const month_day_last february_last = February / last;

  EXPECT_EQ(february_last.month(), February);
  EXPECT_TRUE(february_last.ok());

  const year_month_day_last leap{2024y, february_last};
  const year_month_day_last common{2023y, february_last};
  EXPECT_EQ(leap.day(), day{29});
  EXPECT_EQ(common.day(), day{28});
}

TEST(MonthWeekday, ItStoresARecurringRuleWithoutAYear) {
  const month_weekday second_monday = March / Monday[2];
  const month_weekday_last last_friday = March / Friday[last];

  EXPECT_EQ(second_monday.month(), March);
  EXPECT_EQ(second_monday.weekday_indexed().weekday(), Monday);
  EXPECT_EQ(second_monday.weekday_indexed().index(), 2U);
  EXPECT_TRUE(second_monday.ok());

  EXPECT_EQ(last_friday.month(), March);
  EXPECT_EQ(last_friday.weekday_last().weekday(), Friday);
  EXPECT_TRUE(last_friday.ok());

  // 这些类型适合表达“每年三月第二个周一”之类规则；加入 year 后才能得到具体日期。
}

TEST(YearMonth, MonthArithmeticCarriesIntoTheYearField) {
  year_month value = 2024y / November;
  value += months{3};

  EXPECT_EQ(value.year(), 2025y);
  EXPECT_EQ(value.month(), February);
  EXPECT_TRUE(value.ok());

  value -= years{2};
  EXPECT_EQ(value, 2023y / February);
  EXPECT_EQ((2025y / April) - (2024y / December), months{4});

  // 与裸 month 的模 12 算术不同，year_month 同时调整 year，因此差值可跨年并带符号。
}

TEST(YearMonthDay, GettersAndOkValidateTheCompleteCivilDate) {
  const year_month_day leap_day = 2024y / February / 29d;
  const year_month_day common_year_invalid = 2023y / February / 29d;

  EXPECT_EQ(leap_day.year(), 2024y);
  EXPECT_EQ(leap_day.month(), February);
  EXPECT_EQ(leap_day.day(), 29d);
  EXPECT_TRUE(leap_day.ok());
  EXPECT_FALSE(common_year_invalid.ok());
  EXPECT_LT(2024y / February / 29d, 2024y / March / 1d);
}

TEST(YearMonthDay, SysDaysRoundTripCreatesATimelinePoint) {
  const year_month_day civil = 2024y / February / 29d;
  const sys_days timeline{civil};
  const year_month_day next{timeline + days{1}};
  const year_month_day previous{timeline - days{1}};

  EXPECT_EQ(year_month_day{timeline}, civil);
  EXPECT_EQ(next, 2024y / March / 1d);
  EXPECT_EQ(previous, 2024y / February / 28d);

  // sys_days 是连续天数时间线，days 算术会正确跨月、闰日和年份；这和直接修改 day
  // 字段完全不同。
}

TEST(YearMonthDay, LocalDaysUsesTheSameCivilConversionInALocalClockDomain) {
  const year_month_day civil = 2030y / June / 15d;
  const local_days local_point{civil};

  EXPECT_EQ(year_month_day{local_point}, civil);
  static_assert(std::is_same_v<local_days,
                               time_point<local_t, days>>);

  // local_days 仍未选择时区；它只把日历日期放进 local_t 的天粒度时间线。
}

TEST(YearMonthDay, InvalidFieldsNormalizeOnlyWhenConvertedToDayTimeline) {
  const year_month_day invalid = 2021y / February / 31d;
  ASSERT_FALSE(invalid.ok());

  const sys_days normalized_point{invalid};
  const year_month_day normalized{normalized_point};
  EXPECT_EQ(normalized, 2021y / March / 3d);

  // year_month_day 构造不会自动修正字段；显式转 sys_days 时按“当月一日 + day-1”
  // 计算，才得到归一化日期。验证输入时必须先看 ok()，不能让转换悄悄接受 2 月 31 日。
}

TEST(YearMonthDay, AddingMonthsPreservesTheDayFieldInsteadOfClamping) {
  const year_month_day january_end = 2021y / January / 31d;
  const year_month_day one_month_later = january_end + months{1};

  EXPECT_EQ(one_month_later.year(), 2021y);
  EXPECT_EQ(one_month_later.month(), February);
  EXPECT_EQ(one_month_later.day(), 31d);
  EXPECT_FALSE(one_month_later.ok());

  // 月历算术保留 day=31，并不会自动选二月最后一天。需要“月底跟随”语义时应使用
  // year_month_day_last，或在业务层显式选择 clamp 策略。
}

TEST(YearMonthDay, AddingYearsCanMakeALeapDayInvalid) {
  const year_month_day leap_day = 2024y / February / 29d;
  const year_month_day next_year = leap_day + years{1};

  EXPECT_EQ(next_year, 2025y / February / 29d);
  EXPECT_FALSE(next_year.ok());

  // years 算术同样保留月日字段，不把周年纪念日偷偷改成 2 月 28 日或 3 月 1 日。
}

TEST(YearMonthDayLast, MonthAndYearArithmeticKeepsLastDaySemantics) {
  year_month_day_last value = 2024y / February / last;
  EXPECT_EQ(value.day(), 29d);

  value += years{1};
  EXPECT_EQ(value.year(), 2025y);
  EXPECT_EQ(value.month(), February);
  EXPECT_EQ(value.day(), 28d);

  value += months{1};
  EXPECT_EQ(value, 2025y / March / last);
  EXPECT_EQ(value.day(), 31d);

  // 此类型保存“last”规则而非固定 day 数值，所以跨月/跨年后重新计算真实月底。
}

TEST(YearMonthWeekday, IndexedRuleConvertsToTheConcreteOccurrence) {
  const year_month_weekday second_monday = 2024y / January / Monday[2];

  EXPECT_TRUE(second_monday.ok());
  EXPECT_EQ(second_monday.year(), 2024y);
  EXPECT_EQ(second_monday.month(), January);
  EXPECT_EQ(second_monday.weekday_indexed().weekday(), Monday);
  EXPECT_EQ(year_month_day{sys_days{second_monday}},
            2024y / January / 8d);
}

TEST(YearMonthWeekday, StructurallyValidFifthOccurrenceMayNotExistThatMonth) {
  const year_month_weekday fifth_monday = 2021y / February / Monday[5];

  EXPECT_TRUE(fifth_monday.weekday_indexed().ok());
  EXPECT_FALSE(fifth_monday.ok());
  EXPECT_EQ(year_month_day{sys_days{fifth_monday}}, 2021y / March / 1d);

  // Monday[5] 自身结构有效，但 2021 年 2 月只有四个周一。组合 ok() 才回答该月是否
  // 真有第五次；转换仍按公式落到下个月，不能代替输入验证。
}

TEST(YearMonthWeekdayLast, LastRuleAlwaysFindsAnOccurrenceInAValidMonth) {
  const year_month_weekday_last last_friday =
      2024y / February / Friday[last];

  EXPECT_TRUE(last_friday.ok());
  EXPECT_EQ(year_month_day{sys_days{last_friday}},
            2024y / February / 23d);
}

TEST(CalendarSyntax, SlashOperatorsAllowEquivalentNaturalOrders) {
  const year_month_day year_first = 2024y / February / 29d;
  const year_month_day month_first = February / 29d / 2024y;
  const year_month_day direct{2024y, February, 29d};
  const year_month_day_last explicit_last{
      2024y, month_day_last{February}};
  const year_month_weekday explicit_first_monday{
      2024y, February, Monday[1]};

  EXPECT_EQ(year_first, month_first);
  EXPECT_EQ(month_first, direct);
  EXPECT_EQ(2024y / February / last, explicit_last);
  EXPECT_EQ(2024y / February / Monday[1], explicit_first_monday);

  // `/` 在这里是强类型日历组合运算符，不是数值除法；中间操作数类型决定后续可拼接
  // 的字段，使用 year/month/day 的强类型可避免裸整数顺序歧义。
}

TEST(CalendarDurations, MonthsAndYearsAreAverageDurationsNotVariableCalendarUnits) {
  static_assert(months::period::num == 2'629'746);
  static_assert(months::period::den == 1);
  static_assert(years::period::num == 31'556'952);
  static_assert(years::period::den == 1);

  const auto average_month_hours = duration_cast<hours>(months{1});
  EXPECT_EQ(average_month_hours, hours{730});

  // duration<months> 用公历 400 年平均月长，duration<years> 用平均年长；它们适合单位
  // 换算，不代表某个具体月的 28–31 天。具体日历移动要用 year_month_day + months。
}

}  // namespace
