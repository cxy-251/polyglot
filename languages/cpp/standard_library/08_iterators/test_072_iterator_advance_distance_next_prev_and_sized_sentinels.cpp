// polyglot-covers:
// - cpp.stdlib.iterators.std-advance-positive-and-negative
// - cpp.stdlib.iterators.std-distance-complexity-by-category
// - cpp.stdlib.iterators.std-next-and-prev-nonmutating-navigation
// - cpp.stdlib.iterators.ranges-advance-count-bound-and-remainder
// - cpp.stdlib.iterators.ranges-distance-iterator-sentinel-and-range
// - cpp.stdlib.iterators.sentinel-for-different-end-type
// - cpp.stdlib.iterators.sized-sentinel-for-constant-time-distance
// - cpp.stdlib.iterators.ranges-next-and-prev-bounded-navigation

#include <gtest/gtest.h>

#include <array>
#include <concepts>
#include <cstddef>
#include <iterator>
#include <list>
#include <ranges>
#include <type_traits>
#include <vector>

namespace {

struct CountingIterator {
  using value_type = int;
  using difference_type = std::ptrdiff_t;
  using iterator_concept = std::forward_iterator_tag;
  using iterator_category = std::forward_iterator_tag;

  static inline int increments = 0;
  int* current = nullptr;

  int& operator*() const noexcept {
    return *current;
  }

  CountingIterator& operator++() noexcept {
    ++increments;
    ++current;
    return *this;
  }

  CountingIterator operator++(int) noexcept {
    auto old = *this;
    ++*this;
    return old;
  }

  friend bool operator==(
      const CountingIterator&,
      const CountingIterator&) = default;
};

struct UnsizedSentinel {
  int* end = nullptr;

  friend bool operator==(CountingIterator iterator, UnsizedSentinel sentinel) {
    return iterator.current == sentinel.end;
  }
};

struct SizedSentinel {
  int* end = nullptr;

  friend bool operator==(CountingIterator iterator, SizedSentinel sentinel) {
    return iterator.current == sentinel.end;
  }

  friend std::ptrdiff_t operator-(SizedSentinel sentinel, CountingIterator iterator) {
    return sentinel.end - iterator.current;
  }

  friend std::ptrdiff_t operator-(CountingIterator iterator, SizedSentinel sentinel) {
    return iterator.current - sentinel.end;
  }
};

TEST(IteratorOperations, AdvanceUsesTheOperationsAvailableAtTheIteratorCategory) {
  std::list<int> values{1, 2, 3, 4, 5};
  auto iterator = values.begin();

  std::advance(iterator, 3);
  EXPECT_EQ(*iterator, 4);

  std::advance(iterator, -2);
  EXPECT_EQ(*iterator, 2);

  // std::advance 对 random-access iterator 可直接 +=，对其他类别逐步 ++；负距离只对
  // bidirectional/random-access 有效。越过合法范围没有自动检查，会违反迭代器前置条件。
}

TEST(IteratorOperations, DistanceHasCategoryDependentComplexityAndDirectionRules) {
  std::vector<int> contiguous{1, 2, 3, 4};
  std::list<int> linked{1, 2, 3, 4};

  EXPECT_EQ(std::distance(contiguous.begin(), contiguous.end()), 4);
  EXPECT_EQ(std::distance(contiguous.end(), contiguous.begin()), -4);
  EXPECT_EQ(std::distance(linked.begin(), linked.end()), 4);

  // random-access 距离用 last-first，为常数时间并可在反向可达时为负；其他 iterator
  // 从 first 递增到 last，为线性时间。若 last 从 first 不可达，调用没有可靠结果。
}

TEST(IteratorOperations, NextAndPrevReturnNewIteratorsWithoutChangingTheOriginal) {
  std::list<int> values{1, 2, 3, 4};
  auto first = values.begin();

  auto third = std::next(first, 2);
  auto second = std::prev(third);

  EXPECT_EQ(*first, 1);
  EXPECT_EQ(*second, 2);
  EXPECT_EQ(*third, 3);

  // next/prev 复制 iterator 后调用 advance，适合在表达式中导航；原 iterator 不变。
  // prev 需要可后退的 iterator，不能用于只有单向能力的 forward_list iterator。
}

TEST(Sentinels, EndConditionCanHaveADifferentTypeFromTheIterator) {
  std::array<int, 4> values{2, 3, 5, 7};
  CountingIterator first{values.data()};
  UnsizedSentinel last{values.data() + values.size()};

  static_assert(std::sentinel_for<UnsizedSentinel, CountingIterator>);
  static_assert(!std::sized_sentinel_for<UnsizedSentinel, CountingIterator>);

  int sum = 0;
  for (; first != last; ++first) {
    sum += *first;
  }
  EXPECT_EQ(sum, 17);

  // C++20 sentinel 只需与 iterator 比较结束条件，不必是同一类型，也不必可解引用。
  // 这允许用计数、终止字符或外部状态表达结尾，而无需制造一个“末尾 iterator”。
}

TEST(RangesDistance, UnsizedSentinelRequiresIncrementingToTheEnd) {
  std::array<int, 4> values{1, 2, 3, 4};
  CountingIterator first{values.data()};
  UnsizedSentinel last{values.data() + values.size()};
  CountingIterator::increments = 0;

  const auto distance = std::ranges::distance(first, last);

  EXPECT_EQ(distance, 4);
  EXPECT_EQ(CountingIterator::increments, 4);

  // 没有 sentinel-iterator 减法时，ranges::distance 复制 first 并逐步递增；调用者的
  // first 不变，但单遍输入 iterator 的共享数据源仍可能有消费语义。
}

TEST(RangesDistance, SizedSentinelProvidesDistanceWithoutIncrementing) {
  std::array<int, 5> values{1, 2, 3, 4, 5};
  CountingIterator first{values.data()};
  SizedSentinel last{values.data() + values.size()};
  CountingIterator::increments = 0;

  static_assert(std::sized_sentinel_for<SizedSentinel, CountingIterator>);
  const auto distance = std::ranges::distance(first, last);

  EXPECT_EQ(distance, 5);
  EXPECT_EQ(CountingIterator::increments, 0);

  // sized_sentinel_for 要求两个方向的减法一致，ranges::distance 因而能直接求差。
  // 自定义 iterator 不能为追求性能谎报该概念；减法必须是常数时间且数值正确。
}

TEST(RangesDistance, RangeOverloadUsesBeginEndAndReturnsSignedDifference) {
  std::array<int, 3> values{2, 3, 5};

  const auto distance = std::ranges::distance(values);

  static_assert(std::is_same_v<decltype(distance), const std::ptrdiff_t>);
  EXPECT_EQ(distance, 3);

  // range overload 等价地从 ranges::begin/end 获取 iterator 与 sentinel；结果是
  // range_difference_t 的有符号距离，不是容器的无符号 size_type。
}

TEST(RangesAdvance, BoundStopsTraversalAndReturnsTheUnconsumedDistance) {
  std::array<int, 4> values{1, 2, 3, 4};
  auto iterator = values.begin();

  const auto remainder = std::ranges::advance(iterator, 10, values.end());

  EXPECT_EQ(iterator, values.end());
  EXPECT_EQ(remainder, 6);

  iterator = values.begin();
  const auto none = std::ranges::advance(iterator, 2, values.end());
  EXPECT_EQ(*iterator, 3);
  EXPECT_EQ(none, 0);

  // 三参数 advance 最多移动到 bound，并返回尚未消费的 n；这比无界 advance 更适合
  // 处理短 range。n 与 bound 方向必须一致，否则仍不构成合法导航。
}

TEST(RangesNavigation, NextAndPrevAlsoOfferBoundedOverloads) {
  std::array<int, 5> values{1, 2, 3, 4, 5};

  auto end = std::ranges::next(values.begin(), 20, values.end());
  auto fourth = std::ranges::prev(values.end(), 2, values.begin());
  auto second = std::ranges::next(values.begin(), 1);

  EXPECT_EQ(end, values.end());
  EXPECT_EQ(*fourth, 4);
  EXPECT_EQ(*second, 2);

  // ranges::next/prev 同样返回副本；带 bound 的版本不会越过给定边界。prev 的 bound
  // 位于后退方向，且仍要求 bidirectional iterator。
}

}  // namespace
