// 时长、时钟与单调时间。
// 共同问题：时长与时间点如何运算；墙上时钟和单调时钟分别回答什么；
// 测量经过时间是否依赖真实等待或日历时间。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: durations_clocks_and_monotonic_time
// polyglot-related: languages/cpp/standard_library/12_time/
// polyglot-related+: test_110_duration_period_conversions_arithmetic_rounding_and_literals.cpp

#include <gtest/gtest.h>

#include <chrono>
#include <type_traits>

namespace {

using namespace std::chrono_literals;

TEST(ClockConcept, DurationsConvertThroughExplicitUnits) {
  const auto duration = 1min + 30s;

  EXPECT_EQ(std::chrono::duration_cast<std::chrono::seconds>(duration).count(), 90);
  EXPECT_EQ(duration * 2, 3min);
}

TEST(ClockConcept, TimePointArithmeticProducesDurationsAndTimePoints) {
  const std::chrono::steady_clock::time_point start{10s};
  const auto finish = start + 250ms;

  EXPECT_EQ(finish - start, 250ms);
}

TEST(ClockConcept, SteadyClockIsSuitableForElapsedTime) {
  static_assert(std::chrono::steady_clock::is_steady);
  const auto first = std::chrono::steady_clock::now();
  const auto second = std::chrono::steady_clock::now();

  EXPECT_GE(second, first);
}

TEST(ClockConcept, DifferentClockEpochsAreDifferentTypes) {
  constexpr bool same_time_point_type =
      std::is_same_v<std::chrono::steady_clock::time_point,
                     std::chrono::system_clock::time_point>;
  static_assert(!same_time_point_type);

  // system_clock 可映射日历时间；steady_clock 只保证单调，二者时间点不能直接相减。
  EXPECT_FALSE(same_time_point_type);
}

}  // namespace
