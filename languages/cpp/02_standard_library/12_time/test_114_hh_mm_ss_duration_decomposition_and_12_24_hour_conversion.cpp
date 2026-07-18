// polyglot-covers:
// - cpp.stdlib.chrono.hh-mm-ss-sign-hours-minutes-seconds-subseconds
// - cpp.stdlib.chrono.hh-mm-ss-precision-and-fractional-width
// - cpp.stdlib.chrono.hh-mm-ss-class-template-argument-deduction
// - cpp.stdlib.chrono.hh-mm-ss-to-duration-round-trip
// - cpp.stdlib.chrono.hh-mm-ss-hours-can-exceed-clock-day
// - cpp.stdlib.chrono.is-am-is-pm-half-day-classification
// - cpp.stdlib.chrono.make12-midnight-noon-and-hour-conversion
// - cpp.stdlib.chrono.make24-am-pm-to-day-hour-conversion

#include <gtest/gtest.h>

#include <chrono>
#include <ratio>
#include <type_traits>

namespace {

using namespace std::chrono;
using namespace std::chrono_literals;

TEST(HhMmSs, PositiveDurationSplitsIntoClockLikeComponents) {
  const hh_mm_ss value{3h + 14min + 15s + 926ms};

  EXPECT_FALSE(value.is_negative());
  EXPECT_EQ(value.hours(), 3h);
  EXPECT_EQ(value.minutes(), 14min);
  EXPECT_EQ(value.seconds(), 15s);
  EXPECT_EQ(value.subseconds(), 926ms);

  // hh_mm_ss 是 duration 的结构化分解，不是带日期或时区的时间点。
}

TEST(HhMmSs, NegativeDurationStoresSignSeparatelyFromAbsoluteComponents) {
  const hh_mm_ss value{-(1h + 2min + 3s + 4ms)};

  EXPECT_TRUE(value.is_negative());
  EXPECT_EQ(value.hours(), 1h);
  EXPECT_EQ(value.minutes(), 2min);
  EXPECT_EQ(value.seconds(), 3s);
  EXPECT_EQ(value.subseconds(), 4ms);

  // 负号不只附着在 hours 上；所有分量访问器返回绝对值部分，is_negative 单独记录符号。
}

TEST(HhMmSs, FractionalWidthMatchesExactDecimalTickResolution) {
  using MillisecondClock = hh_mm_ss<milliseconds>;
  using MicrosecondClock = hh_mm_ss<microseconds>;
  using ThirdSeconds = duration<int, std::ratio<1, 3>>;
  using RepeatingClock = hh_mm_ss<ThirdSeconds>;

  static_assert(MillisecondClock::fractional_width == 3U);
  static_assert(MicrosecondClock::fractional_width == 6U);
  static_assert(RepeatingClock::fractional_width == 6U);
  static_assert(std::is_same_v<MillisecondClock::precision, milliseconds>);

  EXPECT_EQ(MillisecondClock{1234ms}.subseconds(), 234ms);

  // fractional_width 是精确十进制位数；若原周期不能用 10 的幂精确表达（如 1/3 秒），
  // 标准回退到 6 位，而不是声称能无穷展开。
}

TEST(HhMmSs, DeductionGuidePreservesTheInputDurationResolution) {
  const hh_mm_ss deduced{microseconds{1'234'567}};

  static_assert(std::is_same_v<decltype(deduced),
                               const hh_mm_ss<microseconds>>);
  EXPECT_EQ(deduced.hours(), 0h);
  EXPECT_EQ(deduced.minutes(), 0min);
  EXPECT_EQ(deduced.seconds(), 1s);
  EXPECT_EQ(deduced.subseconds(), 234'567us);

  // CTAD 从实参 duration 推导模板参数，避免手写一个较粗 Duration 后提前丢失亚秒。
}

TEST(HhMmSs, ToDurationAndExplicitConversionReassembleTheSignedValue) {
  const hh_mm_ss<milliseconds> positive{3'723'456ms};
  const hh_mm_ss<milliseconds> negative{-3'723'456ms};

  EXPECT_EQ(positive.to_duration(), 3'723'456ms);
  EXPECT_EQ(static_cast<milliseconds>(positive), 3'723'456ms);
  EXPECT_EQ(negative.to_duration(), -3'723'456ms);

  // to_duration 使用 precision 类型重组，调用者仍须保证总小时数可由 rep 表示。
}

TEST(HhMmSs, HoursAreNotAutomaticallyReducedModuloTwentyFour) {
  const hh_mm_ss value{49h + 5min};

  EXPECT_EQ(value.hours(), 49h);
  EXPECT_EQ(value.minutes(), 5min);
  EXPECT_EQ(value.to_duration(), 49h + 5min);

  // 拆分任意 elapsed duration 时 hours 可以超过 23；若要“当天时刻”，应先按 days
  // 分离日期或显式取模，并仔细处理负值。
}

TEST(HalfDayClassification, IsAmAndIsPmCoverOnlyCanonicalDayHours) {
  EXPECT_TRUE(is_am(0h));
  EXPECT_TRUE(is_am(11h));
  EXPECT_FALSE(is_am(12h));
  EXPECT_FALSE(is_am(24h));

  EXPECT_FALSE(is_pm(11h));
  EXPECT_TRUE(is_pm(12h));
  EXPECT_TRUE(is_pm(23h));
  EXPECT_FALSE(is_pm(24h));

  // 这两个谓词的有效分类范围是 [0h,24h)，不会自动把 24h 或负小时按一天取模。
}

TEST(Make12, MidnightAndNoonBothDisplayAsTwelve) {
  EXPECT_EQ(make12(0h), 12h);
  EXPECT_EQ(make12(12h), 12h);
  EXPECT_EQ(make12(13h), 1h);
  EXPECT_EQ(make12(23h), 11h);

  // 单靠 12 小时显示值无法区分午夜与正午，必须同时保存 AM/PM 信息。
}

TEST(Make24, AmPmFlagDisambiguatesTwelveHourInput) {
  EXPECT_EQ(make24(12h, false), 0h);
  EXPECT_EQ(make24(12h, true), 12h);
  EXPECT_EQ(make24(1h, false), 1h);
  EXPECT_EQ(make24(1h, true), 13h);
  EXPECT_EQ(make24(11h, true), 23h);

  // 第二个参数为 true 表示 PM。输入应是 [1h,12h] 的 12 小时制值；不要先把午夜写成
  // 0h 再交给 make24。
}

constexpr hh_mm_ss kCompileTimeSplit{90min + 250ms};
static_assert(kCompileTimeSplit.hours() == 1h);
static_assert(kCompileTimeSplit.minutes() == 30min);
static_assert(kCompileTimeSplit.subseconds() == 250ms);

}  // namespace
