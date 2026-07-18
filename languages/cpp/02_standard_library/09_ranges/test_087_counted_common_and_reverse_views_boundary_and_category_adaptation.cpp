// polyglot-covers:
// - cpp.stdlib.ranges.views-counted-contiguous-span-optimization
// - cpp.stdlib.ranges.views-counted-noncontiguous-counted-iterator
// - cpp.stdlib.ranges.views-counted-count-precondition-and-boundary
// - cpp.stdlib.ranges.common-view-unifies-different-sentinel-type
// - cpp.stdlib.ranges.views-common-already-common-range-optimization
// - cpp.stdlib.ranges.common-view-classic-algorithm-interoperability
// - cpp.stdlib.ranges.reverse-view-order-reference-and-base
// - cpp.stdlib.ranges.reverse-view-category-size-and-double-reverse
// - cpp.stdlib.ranges.reverse-view-begin-cache-for-non-common-range

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <iterator>
#include <list>
#include <ranges>
#include <span>
#include <type_traits>
#include <vector>

namespace {

template <std::ranges::input_range Range>
auto CollectRange(Range&& range) {
  std::vector<std::ranges::range_value_t<Range>> result;
  std::ranges::copy(range, std::back_inserter(result));
  return result;
}

TEST(CountedView, ContiguousIteratorUsesASpanLikeOptimizedResult) {
  int values[] = {1, 2, 3, 4};
  auto first_three = std::views::counted(values, 3);

  static_assert(std::ranges::contiguous_range<decltype(first_three)>);
  static_assert(std::ranges::sized_range<decltype(first_three)>);

  EXPECT_EQ(first_three.data(), values);
  EXPECT_EQ(first_three.size(), 3U);
  first_three[1] = 20;
  EXPECT_EQ(values[1], 20);

  if constexpr (!std::is_same_v<decltype(first_three), std::span<int>>) {
    GTEST_SKIP() << "libstdc++ 11 未实现 N4861 要求的 counted(pointer,n) span 优化";
  }

  // N4861 要求 views::counted(pointer,n) 直接返回 dynamic-extent span，保留地址与 size；
  // libstdc++ 11 的早期实现仍返回等价的 contiguous subrange，因此用特性检测明确记录缺口。
  // 它不验证指针后确有 n 个元素，调用者必须保证整个半开区间可解引用。
}

TEST(CountedView, NoncontiguousIteratorUsesCountedIteratorAndDefaultSentinel) {
  std::list<int> values{2, 3, 5, 7};
  auto first_three = std::views::counted(values.begin(), 3);

  static_assert(std::ranges::sized_range<decltype(first_three)>);
  static_assert(!std::ranges::common_range<decltype(first_three)>);
  static_assert(std::ranges::bidirectional_range<decltype(first_three)>);

  EXPECT_EQ(CollectRange(first_three), (std::vector<int>{2, 3, 5}));
  EXPECT_EQ(first_three.size(), 3U);

  // 对非随机访问 iterator，counted 组合 counted_iterator 与 default_sentinel；距离由
  // count 常数时间给出，但首尾类型不同。count 必须非负且不能超过真实可达元素数。
}

TEST(CountedView, ZeroCountProducesAnEmptyRangeAtTheOriginalPosition) {
  std::array<int, 2> values{1, 2};
  auto none = std::views::counted(values.begin(), 0);

  EXPECT_TRUE(none.empty());
  EXPECT_EQ(none.size(), 0U);
  EXPECT_EQ(none.data(), values.data());

  // n==0 是有效空 range，起始指针仍可等于原位置但不可通过该 view 解引用；负 n 违反
  // 前置条件。counted 不是边界检查器，只把已知计数编码为 sentinel。
}

TEST(CommonView, ItWrapsADifferentSentinelRangeForLegacySameTypeInterfaces) {
  int values[] = {2, 3, 5, 7};
  auto counted = std::ranges::subrange(
      std::counted_iterator{values, 3},
      std::default_sentinel);
  auto common = counted | std::views::common;

  static_assert(!std::ranges::common_range<decltype(counted)>);
  static_assert(std::ranges::common_range<decltype(common)>);
  static_assert(std::is_same_v<
                std::ranges::iterator_t<decltype(common)>,
                std::ranges::sentinel_t<decltype(common)>>);

  std::vector<int> copied;
  std::copy(common.begin(), common.end(), std::back_inserter(copied));
  EXPECT_EQ(copied, (std::vector<int>{2, 3, 5}));

  // common_view 通常用 common_iterator<I,S> 统一首尾，便于只接受同类型 pair 的经典
  // 算法。原生 ranges 算法直接支持 sentinel，没必要无条件增加这层适配。
}

TEST(CommonView, ApplyingItToAnAlreadyCommonRangeKeepsAnAllView) {
  std::vector<int> values{1, 2, 3};
  auto common = values | std::views::common;

  static_assert(std::ranges::common_range<decltype(common)>);
  static_assert(std::is_same_v<
                decltype(common),
                std::ranges::ref_view<std::vector<int>>>);
  EXPECT_EQ(common.size(), values.size());

  // views::common 对本来已 common 的 viewable range 直接返回 views::all，不套冗余
  // common_view。adaptor object 可以根据输入概念选择优化后的具体类型。
}

TEST(ReverseView, IterationOrderFlipsWhileReferencesStillAliasTheSource) {
  std::vector<int> values{1, 2, 3, 4};
  auto reversed = values | std::views::reverse;

  EXPECT_EQ(std::vector<int>(reversed.begin(), reversed.end()),
            (std::vector<int>{4, 3, 2, 1}));

  reversed.front() = 40;
  reversed.back() = 10;
  EXPECT_EQ(values, (std::vector<int>{10, 2, 3, 40}));

  // reverse_view 只以 reverse_iterator 翻转遍历方向，reference 仍指向底层元素；
  // reversed.front 对应 source.back。它不反转或复制原容器本身。
}

TEST(ReverseView, RandomAccessSizeAndCommonPropertiesCanBePreserved) {
  std::vector<int> values{1, 2, 3, 4};
  auto reversed = values | std::views::reverse;

  static_assert(std::ranges::random_access_range<decltype(reversed)>);
  static_assert(std::ranges::sized_range<decltype(reversed)>);
  static_assert(std::ranges::common_range<decltype(reversed)>);

  EXPECT_EQ(reversed.size(), 4U);
  EXPECT_EQ(reversed[1], 3);

  auto base = reversed.base();
  static_assert(std::is_same_v<
                decltype(base),
                std::ranges::ref_view<std::vector<int>>>);
  EXPECT_EQ(&base.base(), &values);

  // reverse 不改变元素数量或随机访问复杂度；base() 返回保存的上游 view 副本，
  // 不是“当前 reverse iterator 的 base”。这里它仍通过 ref_view 指向 values。
}

TEST(ReverseView, ApplyingReverseTwiceReturnsTheOriginalDirection) {
  std::vector<int> values{1, 2, 3};
  auto restored = values | std::views::reverse | std::views::reverse;

  EXPECT_EQ(std::vector<int>(restored.begin(), restored.end()), values);
  static_assert(std::is_same_v<
                decltype(restored),
                std::ranges::ref_view<std::vector<int>>>);

  // views::reverse 识别 reverse_view 并取其 base，双重反向可消除适配层；结果仍是
  // 非拥有 ref_view，而不是复制出的 vector。
}

TEST(ReverseView, NonCommonBidirectionalInputMayCacheTheComputedReverseBegin) {
  std::list<int> values{1, 2, 3};
  auto counted = std::ranges::subrange(
      std::counted_iterator{values.begin(), 3},
      std::default_sentinel);
  auto reversed = counted | std::views::reverse;

  EXPECT_EQ(*reversed.begin(), 3);
  EXPECT_EQ(std::vector<int>(reversed.begin(), reversed.end()),
            (std::vector<int>{3, 2, 1}));

  // non-common 上游没有现成 iterator end，reverse_view 首次 begin 需 advance 到 sentinel，
  // 并可缓存结果。底层结构变化后旧缓存/iterator 可能失效，应重建 view。
}

}  // namespace
