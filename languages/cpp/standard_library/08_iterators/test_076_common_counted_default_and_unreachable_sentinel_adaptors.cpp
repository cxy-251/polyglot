// polyglot-covers:
// - cpp.stdlib.iterators.common-iterator-unifies-iterator-and-sentinel-types
// - cpp.stdlib.iterators.common-iterator-legacy-algorithm-interoperability
// - cpp.stdlib.iterators.common-iterator-arrow-and-concept-cap
// - cpp.stdlib.iterators.counted-iterator-base-count-and-navigation
// - cpp.stdlib.iterators.counted-iterator-default-sentinel-and-distance
// - cpp.stdlib.iterators.counted-iterator-iter-move-and-iter-swap
// - cpp.stdlib.iterators.default-sentinel-stateless-end-marker
// - cpp.stdlib.iterators.unreachable-sentinel-infinite-range-marker

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <cstddef>
#include <iterator>
#include <ranges>
#include <string>
#include <type_traits>
#include <vector>

namespace {

TEST(CommonIterator, ItStoresEitherAnIteratorOrADifferentSentinel) {
  std::array<int, 4> values{2, 3, 5, 7};
  using Counted = std::counted_iterator<int*>;
  using Common = std::common_iterator<Counted, std::default_sentinel_t>;

  Common first{Counted{values.data(), 3}};
  Common last{std::default_sentinel};
  std::vector<int> observed;

  for (; first != last; ++first) {
    observed.push_back(*first);
  }

  EXPECT_EQ(observed, (std::vector<int>{2, 3, 5}));

  // common_iterator 内部保存 I 或 S，把不同类型的 iterator/sentinel 暴露为一个公共类型。
  // 它适配旧式“首尾必须同类型”的接口，不会改变原 sentinel 的结束语义。
}

TEST(CommonIterator, ItLetsClassicAlgorithmsConsumeIteratorSentinelRanges) {
  const std::array<int, 4> source{1, 2, 3, 4};
  using Counted = std::counted_iterator<const int*>;
  using Common = std::common_iterator<Counted, std::default_sentinel_t>;
  Common first{Counted{source.data() + 1, 2}};
  Common last{std::default_sentinel};
  std::vector<int> destination;

  std::copy(first, last, std::back_inserter(destination));

  EXPECT_EQ(destination, (std::vector<int>{2, 3}));

  // std::copy 的经典 overload 要求 first/last 同类型；common_iterator 在边界完成桥接。
  // 原生 ranges 算法直接接受 sentinel_for，通常无需这层包装。
}

TEST(CommonIterator, ArrowWorksButTheAdaptorCapsTraversalAtForward) {
  struct Record {
    int value;
  };

  std::array<Record, 2> records{{{7}, {11}}};
  using Common = std::common_iterator<
      std::counted_iterator<Record*>,
      std::default_sentinel_t>;
  Common first{std::counted_iterator{records.data(), 2}};

  EXPECT_EQ(first->value, 7);
  static_assert(std::forward_iterator<Common>);
  static_assert(!std::bidirectional_iterator<Common>);

  // common_iterator 的 iterator_concept 至多是 forward；variant 中的 sentinel 状态没有
  // 可后退位置，因而即使底层是指针也不承诺 bidirectional/random-access。
}

TEST(CountedIterator, CountTracksHowManyDereferenceablePositionsRemain) {
  std::array<std::string, 4> values{"a", "b", "c", "d"};
  std::counted_iterator iterator{values.begin(), 3};

  EXPECT_EQ(iterator.base(), values.begin());
  EXPECT_EQ(iterator.count(), 3);
  EXPECT_EQ(*iterator, "a");

  ++iterator;
  EXPECT_EQ(iterator.base(), values.begin() + 1);
  EXPECT_EQ(iterator.count(), 2);

  iterator += 2;
  EXPECT_EQ(iterator.base(), values.begin() + 3);
  EXPECT_EQ(iterator.count(), 0);

  // counted_iterator 同时保存当前位置与剩余 count；前进 n 会让 count 减 n。
  // 初始 count 必须非负，且底层从当前位置至少能合法前进这么多步。
}

TEST(CountedIterator, DefaultSentinelMarksExactlyCountZero) {
  int values[] = {2, 3, 5, 7};
  std::counted_iterator first{std::begin(values), 3};

  static_assert(std::sentinel_for<std::default_sentinel_t, decltype(first)>);
  static_assert(std::sized_sentinel_for<std::default_sentinel_t, decltype(first)>);
  EXPECT_EQ(std::default_sentinel - first, 3);
  EXPECT_NE(first, std::default_sentinel);

  std::ranges::advance(first, std::default_sentinel);
  EXPECT_EQ(first, std::default_sentinel);
  EXPECT_EQ(first.count(), 0);
  EXPECT_EQ(first.base(), std::begin(values) + 3);

  // default_sentinel 没有边界地址；与 counted_iterator 比较时只检查 count==0，
  // 距离也直接由 count 得出。它可复用于多种知道自身终止条件的 iterator。
}

TEST(CountedIterator, IterMoveAndIterSwapDelegateToTheCurrentBaseElement) {
  std::array<std::string, 2> values{"left", "right"};
  std::counted_iterator left{values.begin(), 2};
  std::counted_iterator right{values.begin() + 1, 1};

  static_assert(std::is_same_v<
                decltype(std::ranges::iter_move(left)),
                std::string&&>);
  std::ranges::iter_swap(left, right);

  EXPECT_EQ(values, (std::array<std::string, 2>{"right", "left"}));
  EXPECT_EQ(left.count(), 2);
  EXPECT_EQ(right.count(), 1);

  // 交换只作用于 base 所指元素，不交换两个适配器的 count；iter_move 同样转发到
  // 当前 base iterator，使底层代理或 ADL 定制继续生效。
}

TEST(DefaultSentinel, TheSingleStatelessObjectCarriesNoRangeSpecificData) {
  static_assert(std::is_empty_v<std::default_sentinel_t>);
  static_assert(
      std::is_same_v<decltype(std::default_sentinel), const std::default_sentinel_t>);

  // default_sentinel 本身不保存地址、长度或回调；具体 iterator 定义如何与它比较。
  // 所以它不能单独描述任意 range 的 end，只是一个共享的标签对象。
}

TEST(UnreachableSentinel, ItNeverComparesEqualToAWeaklyIncrementableIterator) {
  int values[] = {1, 2, 3, 4, 5};
  int* iterator = std::begin(values);

  static_assert(std::sentinel_for<std::unreachable_sentinel_t, int*>);
  EXPECT_FALSE(iterator == std::unreachable_sentinel);

  int sum = 0;
  for (int count = 0; count < 3; ++count, ++iterator) {
    sum += *iterator;
  }
  EXPECT_EQ(sum, 6);

  // unreachable_sentinel 永不相等，适合把可无限递增的生成器表示成无穷 range，再由
  // 外层计数或 take 限制。对它调用无界 distance/find 可能永不结束，本例显式限制三步。
}

}  // namespace
