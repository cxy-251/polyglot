// 生成器、惰性与提前终止。
// 共同问题：何时执行生产逻辑；如何限制消费；提前终止是否运行清理；
// 惰性管道能否重复使用。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/cpp/language/test_021_coroutines_promise_awaiter_and_generator.cpp

#include <gtest/gtest.h>

#include <ranges>
#include <vector>

namespace {

TEST(LazinessConcept, TransformViewRunsOnlyWhenAnElementIsRead) {
  int calls = 0;
  std::vector<int> source{1, 2, 3};
  auto doubled = source | std::views::transform([&calls](int value) {
                   ++calls;
                   return value * 2;
                 });

  EXPECT_EQ(calls, 0);
  EXPECT_EQ(*doubled.begin(), 2);
  EXPECT_EQ(calls, 1);
}

TEST(LazinessConcept, TakeLimitsAnUnboundedIotaView) {
  auto first_three = std::views::iota(10) | std::views::take(3);
  std::vector<int> collected;

  for (int value : first_three) {
    collected.push_back(value);
  }

  EXPECT_EQ(collected, (std::vector<int>{10, 11, 12}));
}

TEST(LazinessConcept, ViewUsuallyReusesTheUnderlyingRange) {
  std::vector<int> source{1, 2};
  auto doubled = source | std::views::transform([](int value) { return value * 2; });

  source[0] = 5;

  EXPECT_EQ(*doubled.begin(), 10);
  EXPECT_EQ(std::ranges::distance(doubled), 2);
}

TEST(LazinessConcept, BreakStopsPullingWithoutAUniversalCloseHook) {
  int calls = 0;
  auto values = std::views::iota(1) | std::views::transform([&calls](int value) {
                  ++calls;
                  return value;
                });

  for (int value : values) {
    EXPECT_EQ(value, 1);
    break;
  }

  EXPECT_EQ(calls, 1);
  // range/view 没有生成器 finally 或 Iterator.return 的通用关闭协议。
}

}  // namespace
