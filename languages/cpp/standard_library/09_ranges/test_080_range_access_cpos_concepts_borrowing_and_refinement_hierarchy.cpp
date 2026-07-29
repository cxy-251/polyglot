// polyglot-covers:
// - cpp.stdlib.ranges.begin-end-cpo-array-member-and-adl-priority
// - cpp.stdlib.ranges.cbegin-cend-rbegin-rend-cpos
// - cpp.stdlib.ranges.size-ssize-empty-data-and-cdata-cpos
// - cpp.stdlib.ranges.range-and-sized-range-concepts
// - cpp.stdlib.ranges.borrowed-range-and-rvalue-access-safety
// - cpp.stdlib.ranges.view-and-viewable-range-concepts
// - cpp.stdlib.ranges.input-forward-bidirectional-random-contiguous-range-hierarchy
// - cpp.stdlib.ranges.common-range-iterator-sentinel-type

#include <gtest/gtest.h>

#include <array>
#include <concepts>
#include <cstddef>
#include <deque>
#include <forward_list>
#include <iterator>
#include <list>
#include <ranges>
#include <span>
#include <type_traits>
#include <utility>
#include <vector>

namespace access_examples {

struct MemberRange {
  int values[3]{1, 2, 3};
  int member_calls = 0;

  int* begin() {
    ++member_calls;
    return values;
  }

  int* end() {
    ++member_calls;
    return values + 3;
  }
};

struct AdlRange {
  int values[3]{4, 5, 6};
  int adl_calls = 0;
};

int* begin(AdlRange& range) {
  ++range.adl_calls;
  return range.values;
}

int* end(AdlRange& range) {
  ++range.adl_calls;
  return range.values + 3;
}

struct BothRange {
  int values[2]{7, 8};
  int member_calls = 0;
  int adl_calls = 0;

  int* begin() {
    ++member_calls;
    return values;
  }

  int* end() {
    ++member_calls;
    return values + 2;
  }
};

int* begin(BothRange& range) {
  ++range.adl_calls;
  return range.values;
}

int* end(BothRange& range) {
  ++range.adl_calls;
  return range.values + 2;
}

}  // namespace access_examples

namespace {

template <class Range>
concept CanBeginTemporary = requires {
  std::ranges::begin(std::declval<Range>());
};

template <class Range>
concept HasRangesData = requires(Range& range) {
  std::ranges::data(range);
};

TEST(RangeAccessCpo, BeginEndPreferArraysThenMembersThenAdl) {
  int raw[] = {10, 20};
  access_examples::MemberRange member;
  access_examples::AdlRange adl;
  access_examples::BothRange both;

  EXPECT_EQ(std::ranges::begin(raw), raw);
  EXPECT_EQ(std::ranges::end(raw), raw + 2);
  EXPECT_EQ(*std::ranges::begin(member), 1);
  EXPECT_EQ(*std::ranges::begin(adl), 4);
  EXPECT_EQ(*std::ranges::begin(both), 7);

  EXPECT_EQ(member.member_calls, 1);
  EXPECT_EQ(adl.adl_calls, 1);
  EXPECT_EQ(both.member_calls, 1);
  EXPECT_EQ(both.adl_calls, 0);

  // ranges::begin/end 是定制点对象：数组直接取边界，其次尝试成员，再尝试仅由 ADL
  // 找到的自由函数。BothRange 证明有效成员会压过同命名空间的 ADL overload。
}

TEST(RangeAccessCpo, ConstAndReverseAccessPreserveElementQualificationAndDirection) {
  std::array<int, 4> values{1, 2, 3, 4};

  auto readonly = std::ranges::cbegin(values);
  auto reverse = std::ranges::rbegin(values);
  auto const_reverse = std::ranges::crbegin(values);

  static_assert(std::is_same_v<decltype(*readonly), const int&>);
  static_assert(std::is_same_v<decltype(*const_reverse), const int&>);
  EXPECT_EQ(*readonly, 1);
  EXPECT_EQ(*reverse, 4);
  EXPECT_EQ(std::ranges::rend(values) - reverse, 4);

  // cbegin/cend 对 range 做 const 访问，rbegin/rend 在可逆 range 上取得反向边界；
  // crbegin/crend 同时施加两者。它们仍不复制或延长底层 range 的寿命。
}

TEST(RangeAccessCpo, SizeEmptyAndSignedSizeExposeDifferentSemanticQuestions) {
  std::vector<int> values{1, 2, 3};
  int raw[] = {4, 5};
  std::forward_list<int> linked{6, 7};

  EXPECT_EQ(std::ranges::size(values), 3U);
  EXPECT_EQ(std::ranges::ssize(values), 3);
  EXPECT_FALSE(std::ranges::empty(values));
  EXPECT_EQ(std::ranges::size(raw), 2U);

  static_assert(std::ranges::sized_range<decltype(values)>);
  static_assert(std::ranges::sized_range<decltype(raw)>);
  static_assert(!std::ranges::sized_range<decltype(linked)>);

  // sized_range 要求 ranges::size 可用且通常为常数时间；forward_list 故意不保存 size。
  // empty 可通过成员、size==0 或 begin==end 回答，因此 unsized range 仍可能支持 empty。
}

TEST(RangeAccessCpo, DataAndCdataRequireContiguousStorage) {
  std::vector<int> values{2, 3, 5};
  int raw[] = {7, 11};

  EXPECT_EQ(std::ranges::data(values), values.data());
  EXPECT_EQ(std::ranges::cdata(values), values.data());
  EXPECT_EQ(std::ranges::data(raw), raw);

  static_assert(std::is_same_v<decltype(std::ranges::data(values)), int*>);
  static_assert(std::is_same_v<decltype(std::ranges::cdata(values)), const int*>);
  static_assert(!HasRangesData<std::list<int>>);

  // data/cdata 只对能产生连续地址的 range 有效；random access 并不足够，deque 也没有
  // 单一 data。cdata 返回只读地址，但同样不携带 size 或所有权。
}

TEST(RangeConcepts, RangeOnlyRequiresBeginAndEndWithAValidSentinelRelationship) {
  static_assert(std::ranges::range<access_examples::MemberRange>);
  static_assert(std::ranges::range<access_examples::AdlRange>);
  static_assert(!std::ranges::range<int*>);
  static_assert(std::ranges::range<int[3]>);

  // range 不要求容器、size、相同首尾类型或所有权，只要求 begin 是
  // input_or_output_iterator，end 对它满足 sentinel_for。裸指针缺少独立的结束边界。
}

TEST(BorrowedRange, TemporaryAccessIsAllowedOnlyWhenIteratorsOutliveTheRangeObject) {
  static_assert(std::ranges::borrowed_range<std::span<int>>);
  static_assert(!std::ranges::borrowed_range<std::vector<int>>);
  static_assert(CanBeginTemporary<std::span<int>&&>);
  static_assert(!CanBeginTemporary<std::vector<int>&&>);

  // ranges::begin 拒绝非 borrowed 的临时 vector，避免立即产生悬空 iterator；span
  // iterator 指向外部存储，销毁 span 对象不影响它。borrowed 不会延长外部存储寿命。
}

TEST(ViewConcepts, ViewsAreCheapRangeObjectsWhileViewableRangeControlsAdaptation) {
  static_assert(std::ranges::view<std::span<int>>);
  static_assert(!std::ranges::view<std::vector<int>>);
  static_assert(std::ranges::viewable_range<std::vector<int>&>);
  static_assert(std::ranges::viewable_range<std::span<int>>);

  // view 是可移动、默认语义为常数时间移动/销毁的 range；vector 拥有动态元素，不是 view。
  // viewable_range 判断对象能否安全交给 view adaptor，lvalue 容器通常通过 ref_view 包装。
}

TEST(RangeRefinements, TraversalConceptsFollowTheUnderlyingIteratorGuarantees) {
  static_assert(std::ranges::forward_range<std::forward_list<int>>);
  static_assert(!std::ranges::bidirectional_range<std::forward_list<int>>);
  static_assert(std::ranges::bidirectional_range<std::list<int>>);
  static_assert(!std::ranges::random_access_range<std::list<int>>);
  static_assert(std::ranges::random_access_range<std::vector<int>>);
  static_assert(std::ranges::contiguous_range<std::vector<int>>);
  static_assert(!std::ranges::contiguous_range<std::deque<int>>);

  // range 层级直接组合 range 与 iterator_t<R> 的对应概念；它描述遍历能力和复杂度，
  // 不表示容器具体类型。算法可按最弱足够概念接收更多自定义 range。
}

TEST(CommonRange, IteratorAndSentinelNeedNotHaveTheSameType) {
  int values[] = {1, 2, 3};
  auto counted = std::ranges::subrange(
      std::counted_iterator{values, 3},
      std::default_sentinel);

  static_assert(std::ranges::range<decltype(counted)>);
  static_assert(!std::ranges::common_range<decltype(counted)>);
  static_assert(std::ranges::common_range<std::vector<int>>);
  EXPECT_EQ(std::ranges::distance(counted), 3);

  // common_range 要求 iterator_t 与 sentinel_t 相同，只是旧接口互操作能力；不同类型
  // 的 sentinel range 仍是完整 C++20 range，可按需用 views::common 做适配。
}

}  // namespace
