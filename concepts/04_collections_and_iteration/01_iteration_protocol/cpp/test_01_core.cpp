// 同步迭代协议。
// 共同问题：如何取得迭代器；推进与完成如何表示；迭代器能否复用；
// 提前退出是否自动触发关闭协议。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/cpp/language/test_005_statements_control_flow_and_range_for.cpp

#include <gtest/gtest.h>

#include <iterator>
#include <ranges>
#include <vector>

namespace {

TEST(IterationProtocolConcept, BeginDereferenceIncrementAndEndExposeTheProtocol) {
  std::vector<int> values{1, 2};
  auto iterator = values.begin();

  EXPECT_EQ(*iterator, 1);
  ++iterator;
  EXPECT_EQ(*iterator, 2);
  ++iterator;
  EXPECT_EQ(iterator, values.end());
}

TEST(IterationProtocolConcept, ContainerCreatesFreshIterators) {
  std::vector<int> values{1, 2};

  EXPECT_EQ(values.begin(), values.begin());
  EXPECT_EQ(std::ranges::distance(values), 2);
  EXPECT_EQ(std::ranges::distance(values), 2);
}

TEST(IterationProtocolConcept, RangeForUsesBeginEndAndIncrement) {
  std::vector<int> values{1, 2, 3};
  int sum = 0;

  for (int value : values) {
    sum += value;
  }

  EXPECT_EQ(sum, 6);
}

TEST(IterationProtocolConcept, IteratorAndSentinelNeedNotHaveOneType) {
  auto values = std::views::iota(1) | std::views::take(3);

  static_assert(std::ranges::range<decltype(values)>);
  EXPECT_EQ(std::ranges::distance(values), 3);

  // C++ iterator/sentinel 协议没有 Python close 或 JavaScript return 的通用提前关闭钩子。
}

}  // namespace
