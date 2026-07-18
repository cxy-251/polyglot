// polyglot-covers:
// - cpp.stdlib.chrono.duration-representation-period-and-custom-tick
// - cpp.stdlib.chrono.duration-value-and-default-initialization
// - cpp.stdlib.chrono.duration-implicit-lossless-conversion-constraints
// - cpp.stdlib.chrono.duration-floating-representation-conversions
// - cpp.stdlib.chrono.duration-common-type-and-mixed-period-arithmetic
// - cpp.stdlib.chrono.duration-scalar-division-ratio-and-modulo
// - cpp.stdlib.chrono.duration-comparison-and-three-way-result
// - cpp.stdlib.chrono.duration-cast-truncation-and-overflow-responsibility
// - cpp.stdlib.chrono.duration-floor-ceil-round-and-ties-to-even
// - cpp.stdlib.chrono.duration-abs-and-min-zero-max
// - cpp.stdlib.chrono.duration-literals-hours-to-nanoseconds
// - cpp.stdlib.chrono.treat-as-floating-point-duration-values-and-common-type

#include <gtest/gtest.h>

#include <chrono>
#include <compare>
#include <cstdint>
#include <limits>
#include <ratio>
#include <type_traits>

namespace {

using namespace std::chrono;

TEST(DurationType, RepresentationAndPeriodDescribeCountAndSecondsPerTick) {
  using VideoFrames = duration<std::int64_t, std::ratio<1, 24>>;
  const VideoFrames frames{48};

  static_assert(std::is_same_v<VideoFrames::rep, std::int64_t>);
  static_assert(VideoFrames::period::num == 1);
  static_assert(VideoFrames::period::den == 24);
  EXPECT_EQ(frames.count(), 48);
  EXPECT_EQ(duration_cast<seconds>(frames), 2s);

  // duration 只保存 tick 数，Period 是编译期“每 tick 多少秒”的有理数，不会作为字段
  // 存进每个对象。24 fps 因而可精确表达为 ratio<1,24>。
}

TEST(DurationConstruction, ValueInitializationProducesZeroButDefaultInitializationIsAConcern) {
  const seconds value_initialized{};
  const seconds explicit_count{3};

  EXPECT_EQ(value_initialized.count(), 0);
  EXPECT_EQ(explicit_count.count(), 3);

  // duration 的默认构造是 defaulted；对内置 rep 写 `seconds d;` 后读取 count 可能读到
  // 未初始化值。使用 `{}` 做值初始化，或直接提供计数。
}

TEST(DurationConstruction, RawCountConstructorIsExplicit) {
  static_assert(std::is_constructible_v<seconds, std::int64_t>);
  static_assert(!std::is_convertible_v<std::int64_t, seconds>);

  const seconds duration_value{5};
  EXPECT_EQ(duration_value, 5s);

  // API 接收 seconds 时调用者不能悄悄传裸整数；显式构造让单位出现在调用点。
}

TEST(DurationConversion, IntegralDurationsConvertImplicitlyOnlyWithoutDivision) {
  static_assert(std::is_convertible_v<milliseconds, microseconds>);
  static_assert(!std::is_convertible_v<microseconds, milliseconds>);
  static_assert(!std::is_constructible_v<milliseconds, microseconds>);

  const milliseconds source{3};
  const microseconds exact = source;
  EXPECT_EQ(exact.count(), 3000);

  const microseconds fractional_source{3500};
  EXPECT_EQ(duration_cast<milliseconds>(fractional_source).count(), 3);

  // integral rep 从细单位转粗单位需要除法，可能截断，因此连直接构造也受约束；必须用
  // duration_cast 明确接受精度损失。
}

TEST(DurationConversion, FloatingRepresentationsAllowFractionalTickConversions) {
  using FloatingSeconds = duration<double>;
  using FloatingMilliseconds = duration<double, std::milli>;

  static_assert(std::is_convertible_v<FloatingMilliseconds, FloatingSeconds>);
  static_assert(std::is_convertible_v<FloatingSeconds, FloatingMilliseconds>);

  const FloatingMilliseconds milliseconds_value{1250.5};
  const FloatingSeconds seconds_value = milliseconds_value;
  EXPECT_DOUBLE_EQ(seconds_value.count(), 1.2505);

  // treat_as_floating_point 为 true 时允许除法转换，因为 rep 能表示小数 tick；仍可能有
  // 浮点舍入误差。
}

TEST(DurationArithmetic, MixedPeriodsUseACommonExactTickPeriod) {
  const seconds whole{1};
  const milliseconds fraction{250};
  const auto sum = whole + fraction;
  const auto difference = whole - fraction;

  static_assert(std::is_same_v<decltype(sum), const milliseconds>);
  EXPECT_EQ(sum.count(), 1250);
  EXPECT_EQ(difference.count(), 750);

  using Common = std::common_type_t<seconds, milliseconds>;
  static_assert(std::is_same_v<Common, milliseconds>);

  // common_type 选择能无损表示双方的最大 tick：周期分子取 gcd、分母取 lcm。这里是
  // 1 ms，而不是较粗的 1 s。
}

TEST(DurationArithmetic, ScalarAndDurationDivisionReturnDifferentKindsOfValues) {
  const seconds elapsed{10};

  EXPECT_EQ(elapsed * 3, 30s);
  EXPECT_EQ(3 * elapsed, 30s);
  EXPECT_EQ(elapsed / 4, seconds{2});
  EXPECT_EQ(elapsed % 4, seconds{2});
  EXPECT_EQ(elapsed / 2500ms, 4);
  EXPECT_EQ(elapsed % 3s, 1s);

  // duration/scalar 仍返回 duration；duration/duration 返回无单位的计数比。integral rep
  // 的标量除法同样向零截断，除数为零没有库级保护。
}

TEST(DurationArithmetic, IncrementAndCompoundOperationsActOnTheStoredCount) {
  milliseconds value{10};

  EXPECT_EQ((value++).count(), 10);
  EXPECT_EQ(value.count(), 11);
  EXPECT_EQ((++value).count(), 12);
  value += 8ms;
  value -= 5ms;
  value *= 2;
  value /= 3;

  EXPECT_EQ(value.count(), 10);
}

TEST(DurationComparison, ValuesAreConvertedBeforeComparison) {
  EXPECT_EQ(1s, 1000ms);
  EXPECT_LT(999ms, 1s);
  EXPECT_GT(1500ms, 1s);

  const auto ordering = 1s <=> 1001ms;
  static_assert(std::is_same_v<decltype(ordering), const std::strong_ordering>);
  EXPECT_EQ(ordering, std::strong_ordering::less);

  // 比较按 common_type 换算，不按原始 count 比较；1 tick 的 seconds 与 1000 ticks 的
  // milliseconds 相等。
}

TEST(DurationCast, IntegralResultTruncatesTowardZero) {
  EXPECT_EQ(duration_cast<seconds>(milliseconds{1999}), 1s);
  EXPECT_EQ(duration_cast<seconds>(milliseconds{-1999}), -1s);

  using SmallMilliseconds = duration<std::int8_t, std::milli>;
  const auto safely_representable =
      duration_cast<SmallMilliseconds>(milliseconds{100});
  EXPECT_EQ(safely_representable.count(), 100);

  // cast 不做饱和或异常式溢出检查；若目标 rep 不能表示转换结果，调用者必须先验证范围。
}

TEST(DurationRounding, FloorCeilAndTruncatingCastDifferForNegativeValues) {
  const milliseconds positive{1500};
  const milliseconds negative{-1500};

  EXPECT_EQ(duration_cast<seconds>(positive), 1s);
  EXPECT_EQ(floor<seconds>(positive), 1s);
  EXPECT_EQ(ceil<seconds>(positive), 2s);

  EXPECT_EQ(duration_cast<seconds>(negative), -1s);
  EXPECT_EQ(floor<seconds>(negative), -2s);
  EXPECT_EQ(ceil<seconds>(negative), -1s);

  // duration_cast 向零截断，不等于数学 floor；负值尤其容易暴露差异。
}

TEST(DurationRounding, RoundUsesNearestWithTiesToEven) {
  EXPECT_EQ(round<seconds>(milliseconds{1499}), 1s);
  EXPECT_EQ(round<seconds>(milliseconds{1500}), 2s);
  EXPECT_EQ(round<seconds>(milliseconds{2500}), 2s);
  EXPECT_EQ(round<seconds>(milliseconds{-1500}), -2s);
  EXPECT_EQ(round<seconds>(milliseconds{-2500}), -2s);

  // 恰好半 tick 时选择偶数 count：1.5 -> 2、2.5 -> 2。目标 duration 的 rep 必须不是
  // 浮点型，避免“舍入到浮点 tick”这个含义不清的接口。
}

TEST(DurationAlgorithms, AbsPreservesTheDurationType) {
  const auto positive = abs(milliseconds{-7});

  static_assert(std::is_same_v<decltype(positive), const milliseconds>);
  EXPECT_EQ(positive, 7ms);

  // abs 只在 rep 可做有符号取负时参与重载；最小有符号计数的绝对值若不可表示，不能拿
  // 它要求库提供饱和行为。
}

TEST(DurationSpecialValues, ZeroMinAndMaxComeFromDurationValues) {
  EXPECT_EQ(seconds::zero().count(), 0);
  EXPECT_EQ(seconds::min().count(),
            std::numeric_limits<seconds::rep>::lowest());
  EXPECT_EQ(seconds::max().count(),
            std::numeric_limits<seconds::rep>::max());

  static_assert(duration_values<int>::zero() == 0);
  static_assert(duration_values<int>::min() ==
                std::numeric_limits<int>::lowest());
  static_assert(duration_values<int>::max() ==
                std::numeric_limits<int>::max());
}

TEST(DurationLiterals, StandardSuffixesEncodeUnitsAndRepresentationChoice) {
  using namespace std::chrono_literals;

  constexpr auto integral = 2h + 30min + 15s + 4ms + 5us + 6ns;
  constexpr auto floating = 1.5s;

  static_assert(std::is_same_v<decltype(2h), hours>);
  static_assert(std::is_same_v<decltype(floating),
                               const duration<long double>>);
  EXPECT_EQ(duration_cast<nanoseconds>(integral),
            nanoseconds{9'015'004'005'006LL});
  EXPECT_DOUBLE_EQ(static_cast<double>(floating.count()), 1.5);

  // 整数字面量使用标准 duration 的整数 rep，浮点字面量使用 long double rep。min 是
  // 分钟后缀，因为 `m` 留给自定义字面量生态中的其他用途。
}

TEST(DurationTraits, FloatingTraitAndCommonRepresentationDriveConversions) {
  static_assert(treat_as_floating_point_v<double>);
  static_assert(!treat_as_floating_point_v<int>);

  using Mixed = std::common_type_t<duration<int, std::ratio<1, 3>>,
                                   duration<double, std::ratio<1, 6>>>;
  static_assert(std::is_same_v<Mixed,
                               duration<double, std::ratio<1, 6>>>);

  const Mixed converted{duration<int, std::ratio<1, 3>>{2}};
  EXPECT_DOUBLE_EQ(converted.count(), 4.0);
}

constexpr milliseconds kCompileTimeDuration = 2s + 500ms;
static_assert(kCompileTimeDuration.count() == 2500);

}  // namespace
