// 同步迭代协议。
// 共同问题：如何取得迭代器；推进与完成如何表示；迭代器能否复用；
// 提前退出是否自动触发关闭协议。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/cpp/standard_library/08_iterators/
// polyglot-related+: test_071_iterator_traits_concepts_indirect_access_and_customization_points.cpp
// polyglot-related: languages/cpp/standard_library/08_iterators/
// polyglot-related+: test_076_common_counted_default_and_unreachable_sentinel_adaptors.cpp

#include <gtest/gtest.h>

#include <concepts>
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
  auto first = values.begin();
  auto second = values.begin();

  ++first;

  EXPECT_EQ(*first, 2);
  EXPECT_EQ(*second, 1);
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
  int values[]{1, 2, 3};
  auto range = std::ranges::subrange{
      std::counted_iterator{values, 3},
      std::default_sentinel,
  };
  int sum = 0;

  static_assert(std::ranges::range<decltype(range)>);
  static_assert(
      !std::same_as<
          std::ranges::iterator_t<decltype(range)>,
          std::ranges::sentinel_t<decltype(range)>>);

  for (int value : range) {
    sum += value;
  }

  EXPECT_EQ(sum, 6);

  // C++ iterator/sentinel 协议没有 Python close 或 JavaScript return 的通用提前关闭钩子。
}

}  // namespace
