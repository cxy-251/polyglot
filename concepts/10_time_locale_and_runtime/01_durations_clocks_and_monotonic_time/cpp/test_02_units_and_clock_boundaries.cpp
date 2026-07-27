// 时长单位和时钟边界。
// 共同问题：时长是否携带单位；墙上时间回拨时经过时间如何计算；
// 数值精度与单位转换由调用方还是类型系统约束。
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

TEST(DurationBoundaryConcept, CommonTypePreservesTheFinerUnit) {
  const auto duration = 1s + 250ms;

  static_assert(std::is_same_v<decltype(duration), const std::chrono::milliseconds>);
  EXPECT_EQ(duration.count(), 1'250);
  EXPECT_EQ(std::chrono::duration_cast<std::chrono::seconds>(duration), 1s);
}

TEST(DurationBoundaryConcept, IntegralCastTruncatesTowardZero) {
  const auto positive = std::chrono::duration_cast<std::chrono::seconds>(1'900ms);
  const auto negative = std::chrono::duration_cast<std::chrono::seconds>(-1'900ms);

  EXPECT_EQ(positive, 1s);
  EXPECT_EQ(negative, -1s);
}

TEST(DurationBoundaryConcept, ClockChoiceDeterminesWhetherRollbackLooksLikeElapsedTime) {
  const std::chrono::system_clock::time_point wall_start{1'000s};
  const std::chrono::system_clock::time_point wall_finish{995s};
  const std::chrono::steady_clock::time_point steady_start{40s};
  const std::chrono::steady_clock::time_point steady_finish{42s + 500ms};

  EXPECT_EQ(wall_finish - wall_start, -5s);
  EXPECT_EQ(steady_finish - steady_start, 2s + 500ms);

  // 注入时间点避免依赖真实校时；不同 clock 的 time_point 不能直接混算。
}

}  // namespace
