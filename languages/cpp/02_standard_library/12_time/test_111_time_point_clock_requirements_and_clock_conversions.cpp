// polyglot-covers:
// - cpp.stdlib.chrono.clock-requirements-custom-clock-and-is-clock-trait
// - cpp.stdlib.chrono.time-point-epoch-duration-and-default-construction
// - cpp.stdlib.chrono.time-point-arithmetic-common-duration-and-difference
// - cpp.stdlib.chrono.time-point-cast-floor-ceil-round
// - cpp.stdlib.chrono.time-point-comparison-min-and-max
// - cpp.stdlib.chrono.system-clock-now-time-t-and-nonsteady-semantics
// - cpp.stdlib.chrono.steady-clock-monotonic-observation
// - cpp.stdlib.chrono.high-resolution-clock-alias-is-implementation-defined
// - cpp.stdlib.chrono.sys-time-and-local-time-aliases
// - cpp.stdlib.chrono.utc-tai-gps-file-clocks-and-clock-cast-feature-gap

#include <gtest/gtest.h>

#include <chrono>
#include <compare>
#include <concepts>
#include <ctime>
#include <ratio>
#include <type_traits>

namespace {

using namespace std::chrono;

struct ManualClock {
  using rep = long long;
  using period = std::milli;
  using duration = std::chrono::duration<rep, period>;
  using time_point = std::chrono::time_point<ManualClock>;
  static constexpr bool is_steady = true;

  static time_point now() noexcept {
    return time_point{duration{42}};
  }
};

struct LooksIncompleteAsAClock {
  using rep = int;
};

template <class Clock>
concept ClockLike = requires {
  typename Clock::rep;
  typename Clock::period;
  typename Clock::duration;
  typename Clock::time_point;
  Clock::is_steady;
  { Clock::now() } -> std::same_as<typename Clock::time_point>;
};

TEST(ClockRequirements, AClockBundlesRepPeriodDurationTimePointAndNow) {
  static_assert(std::is_same_v<ManualClock::duration,
                               duration<long long, std::milli>>);
  static_assert(std::is_same_v<ManualClock::time_point,
                               time_point<ManualClock>>);
  static_assert(ClockLike<ManualClock>);
  static_assert(!ClockLike<LooksIncompleteAsAClock>);
  static_assert(noexcept(ManualClock::now()));

#if defined(__cpp_lib_chrono) && __cpp_lib_chrono >= 201907L
  static_assert(is_clock_v<ManualClock>);
  static_assert(!is_clock_v<LooksIncompleteAsAClock>);
#endif

  EXPECT_EQ(ManualClock::now().time_since_epoch(), 42ms);

  // epoch 由 Clock 自己定义，period 描述时钟 tick。is_clock 至少检查所需嵌套类型、
  // is_steady 和 now 表达式；用户不能通过特化 is_clock 来“补票”。
}

TEST(TimePointConstruction, DefaultValueIsTheClockEpoch) {
  const time_point<ManualClock> epoch;
  const time_point<ManualClock> later{ManualClock::duration{250}};

  EXPECT_EQ(epoch.time_since_epoch(), ManualClock::duration::zero());
  EXPECT_EQ(later.time_since_epoch(), 250ms);

  // time_point 不存日历字段，只保存自 Clock::epoch 起的 duration。默认构造明确得到 epoch，
  // 与内置 rep 的裸 duration 默认初始化风险不同。
}

TEST(TimePointConstruction, FinerDurationConvertsImplicitlyWithoutTruncation) {
  using SecondPoint = time_point<ManualClock, seconds>;
  using MillisecondPoint = time_point<ManualClock, milliseconds>;

  static_assert(std::is_convertible_v<SecondPoint, MillisecondPoint>);
  static_assert(!std::is_convertible_v<MillisecondPoint, SecondPoint>);

  const SecondPoint coarse{2s};
  const MillisecondPoint fine = coarse;
  EXPECT_EQ(fine.time_since_epoch(), 2000ms);
}

TEST(TimePointArithmetic, AddingADurationUsesTheCommonDurationType) {
  using SecondPoint = time_point<ManualClock, seconds>;
  const SecondPoint start{2s};
  const auto later = start + 250ms;
  const auto earlier = 250ms + start - 500ms;

  static_assert(std::is_same_v<decltype(later),
                               const time_point<ManualClock, milliseconds>>);
  EXPECT_EQ(later.time_since_epoch(), 2250ms);
  EXPECT_EQ(earlier.time_since_epoch(), 1750ms);

  // time_point ± duration 仍是时间点，并把内部 duration 提升到 common_type；单位不会因
  // 左右操作数顺序不同而丢失。
}

TEST(TimePointArithmetic, SubtractingTwoPointsReturnsElapsedDuration) {
  const time_point<ManualClock, seconds> start{10s};
  const time_point<ManualClock, milliseconds> finish{12'750ms};
  const auto elapsed = finish - start;

  static_assert(std::is_same_v<decltype(elapsed), const milliseconds>);
  EXPECT_EQ(elapsed, 2750ms);

  // 只有同一 Clock 的时间点可直接相减；不同 epoch 即使 duration 类型相同也没有自动
  // 可比意义，应先使用标准或业务定义的 clock conversion。
}

TEST(TimePointArithmetic, CompoundAssignmentKeepsTheDeclaredDurationType) {
  time_point<ManualClock, milliseconds> point{1000ms};
  point += 250ms;
  point -= 100ms;

  EXPECT_EQ(point.time_since_epoch(), 1150ms);
}

TEST(TimePointCast, CastFloorCeilAndRoundDelegateToDurationSemantics) {
  const time_point<ManualClock, milliseconds> positive{2500ms};
  const time_point<ManualClock, milliseconds> negative{-1500ms};

  EXPECT_EQ(time_point_cast<seconds>(positive).time_since_epoch(), 2s);
  EXPECT_EQ(floor<seconds>(positive).time_since_epoch(), 2s);
  EXPECT_EQ(ceil<seconds>(positive).time_since_epoch(), 3s);
  EXPECT_EQ(round<seconds>(positive).time_since_epoch(), 2s);

  EXPECT_EQ(time_point_cast<seconds>(negative).time_since_epoch(), -1s);
  EXPECT_EQ(floor<seconds>(negative).time_since_epoch(), -2s);
  EXPECT_EQ(ceil<seconds>(negative).time_since_epoch(), -1s);
  EXPECT_EQ(round<seconds>(negative).time_since_epoch(), -2s);

  // cast 向零，floor/ceil 按数学方向，round 在半 tick 取偶数；时间点只是把这些规则
  // 应用于 time_since_epoch。
}

TEST(TimePointComparison, SameClockPointsCompareAfterCommonTypeConversion) {
  const time_point<ManualClock, seconds> whole{1s};
  const time_point<ManualClock, milliseconds> same{1000ms};
  const time_point<ManualClock, milliseconds> later{1001ms};

  EXPECT_EQ(whole, same);
  EXPECT_LT(whole, later);
  EXPECT_EQ(whole <=> later, std::strong_ordering::less);
}

TEST(TimePointSpecialValues, MinAndMaxWrapDurationSpecialValues) {
  using Point = time_point<ManualClock>;

  EXPECT_EQ(Point::min().time_since_epoch(), ManualClock::duration::min());
  EXPECT_EQ(Point::max().time_since_epoch(), ManualClock::duration::max());

  // 对 min 再减、对 max 再加可能让 rep 溢出；time_point 不提供饱和运算。
}

TEST(SystemClock, TimeTConversionRoundTripsAWholeSecondPointWithinItsPrecision) {
  const system_clock::time_point original{seconds{123'456}};
  const std::time_t encoded = system_clock::to_time_t(original);
  const system_clock::time_point decoded = system_clock::from_time_t(encoded);
  const auto error = decoded - original;

  EXPECT_LE(abs(duration_cast<seconds>(error)), 1s);

  // system_clock 是唯一要求能与 time_t 往返的标准时钟。time_t 精度和取整方向由实现
  // 决定，亚秒部分不保证保留，所以协议中应明确序列化单位和 epoch。
}

TEST(SystemClock, NowReturnsAValidPointButTheClockCanBeAdjusted) {
  const system_clock::time_point observed = system_clock::now();

  static_assert(ClockLike<system_clock>);
  static_assert(!system_clock::is_steady);
  EXPECT_GT(observed, system_clock::time_point::min());
  EXPECT_LT(observed, system_clock::time_point::max());

  // 系统时间可被 NTP 或管理员调整，两个连续 now() 也不应被用来断言耗时非负。测量
  // 间隔应使用 steady_clock。
}

TEST(SteadyClock, ConsecutiveObservationsNeverMoveBackward) {
  const steady_clock::time_point first = steady_clock::now();
  const steady_clock::time_point second = steady_clock::now();

  static_assert(ClockLike<steady_clock>);
  static_assert(steady_clock::is_steady);
  EXPECT_LE(first, second);

  // 不用 sleep 测试分辨率；is_steady 保证单调且 tick 周期恒定，不保证两次紧邻调用必然
  // 得到不同值，也不赋予它墙上日期含义。
}

TEST(HighResolutionClock, ItIsAValidClockButMayAliasAnotherStandardClock) {
  static_assert(ClockLike<high_resolution_clock>);
  constexpr bool aliases_system =
      std::is_same_v<high_resolution_clock, system_clock>;
  constexpr bool aliases_steady =
      std::is_same_v<high_resolution_clock, steady_clock>;

  EXPECT_LT(high_resolution_clock::time_point::min(),
            high_resolution_clock::time_point::max());
  if constexpr (aliases_system) {
    EXPECT_FALSE(high_resolution_clock::is_steady);
  } else if constexpr (aliases_steady) {
    EXPECT_TRUE(high_resolution_clock::is_steady);
  }

  // high_resolution_clock 只表示实现提供的最短 tick period，可以是 system_clock、
  // steady_clock 的别名或独立时钟；不能从名字推断 is_steady。
}

TEST(TimeAliases, SysTimeAndLocalTimeEncodeDifferentClockDomains) {
  const sys_seconds system_point{seconds{10}};
  const local_time<milliseconds> local_point{milliseconds{10'500}};

  static_assert(std::is_same_v<sys_seconds,
                               time_point<system_clock, seconds>>);
  static_assert(std::is_same_v<decltype(local_point),
                               const time_point<local_t, milliseconds>>);
  EXPECT_EQ(system_point.time_since_epoch(), 10s);
  EXPECT_EQ(local_point.time_since_epoch(), 10'500ms);

  // local_time 没有关联时区，只是 local_t 域中的时间点；同一个本地读数在夏令时切换处
  // 可能不存在或对应两个 sys_time，必须借助 time_zone 和 choose 策略转换。
}

#if defined(__cpp_lib_chrono) && __cpp_lib_chrono >= 201907L

TEST(Cxx20Clocks, UtcTaiGpsAndFileClocksExposeDistinctEpochs) {
  static_assert(is_clock_v<utc_clock>);
  static_assert(is_clock_v<tai_clock>);
  static_assert(is_clock_v<gps_clock>);
  static_assert(is_clock_v<file_clock>);

  const sys_seconds system_point{seconds{0}};
  const auto utc_point = utc_clock::from_sys(system_point);
  EXPECT_EQ(utc_clock::to_sys(utc_point), system_point);

  const auto tai_point = clock_cast<tai_clock>(utc_point);
  const auto gps_point = clock_cast<gps_clock>(utc_point);
  EXPECT_EQ(clock_cast<utc_clock>(tai_point), utc_point);
  EXPECT_EQ(clock_cast<utc_clock>(gps_point), utc_point);

  // clock_cast 只在唯一转换路径存在时参与重载；不同 clock 的原始 duration 不能直接
  // 当作相同 epoch。UTC 还需要处理闰秒，而 sys_time 不表示闰秒。
}

#else

TEST(Cxx20Clocks, LockedLibstdcxxGapIsRecordedWithoutRemovingCoverage) {
  GTEST_SKIP()
      << "GCC 11 libstdc++ 的 __cpp_lib_chrono 早于 201907L；"
      << "utc/tai/gps/file clocks 与 clock_cast 覆盖已保留，升级工具链后启用";
}

#endif

}  // namespace
