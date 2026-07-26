// polyglot-covers:
// - cpp.stdlib.ranges.view-interface-derived-members
// - cpp.stdlib.ranges.view-interface-conditional-front-back-data-index-and-size
// - cpp.stdlib.ranges.subrange-iterator-sentinel-and-kind
// - cpp.stdlib.ranges.subrange-sized-unsized-and-stored-size
// - cpp.stdlib.ranges.subrange-tuple-interface
// - cpp.stdlib.ranges.subrange-advance-next-and-prev
// - cpp.stdlib.ranges.subrange-is-borrowed-view
// - cpp.stdlib.ranges.borrowed-iterator-and-subrange-aliases
// - cpp.stdlib.ranges.dangling-algorithm-result-for-temporary-owned-range

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <concepts>
#include <cstddef>
#include <ranges>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class IntView : public std::ranges::view_interface<IntView> {
 public:
  IntView() = default;

  IntView(int* first, int* last) : first_(first), last_(last) {}

  int* begin() const noexcept {
    return first_;
  }

  int* end() const noexcept {
    return last_;
  }

 private:
  int* first_ = nullptr;
  int* last_ = nullptr;
};

struct PointerSentinel {
  int* end = nullptr;

  friend bool operator==(int* iterator, PointerSentinel sentinel) {
    return iterator == sentinel.end;
  }
};

TEST(ViewInterface, DerivedMembersAreSynthesizedFromBeginEndAndRangeConcepts) {
  std::array<int, 4> storage{2, 3, 5, 7};
  IntView view{storage.data(), storage.data() + storage.size()};

  static_assert(std::ranges::view<IntView>);
  static_assert(std::ranges::contiguous_range<IntView>);
  static_assert(std::ranges::sized_range<IntView>);

  EXPECT_FALSE(view.empty());
  EXPECT_TRUE(static_cast<bool>(view));
  EXPECT_EQ(view.front(), 2);
  EXPECT_EQ(view.back(), 7);
  EXPECT_EQ(view[2], 5);
  EXPECT_EQ(view.data(), storage.data());
  EXPECT_EQ(view.size(), 4U);

  // view_interface 只需派生类提供 begin/end，就按概念条件合成 empty、bool、front、back、
  // data、size 与 []。它使用 CRTP，不保存 range 边界，也不替派生类管理寿命。
}

TEST(ViewInterface, SynthesizedAccessorsRemainNonOwningAliases) {
  std::array<int, 3> storage{1, 2, 3};
  IntView view{storage.data(), storage.data() + storage.size()};

  view.front() = 10;
  view.back() = 30;
  view[1] = 20;

  EXPECT_EQ(storage, (std::array<int, 3>{10, 20, 30}));

  // 返回类型来自底层 iterator 的 reference，所以可变 view 直接改 storage；
  // view_interface 不复制元素。“const view 对象”与“const 元素 view”仍是不同概念。
}

TEST(Subrange, IteratorSentinelAndKindDescribeTheBoundaryWithoutOwningElements) {
  std::array<int, 5> values{1, 2, 3, 4, 5};
  auto middle = std::ranges::subrange(values.begin() + 1, values.end() - 1);

  using Middle = decltype(middle);
  static_assert(std::ranges::view<Middle>);
  static_assert(std::ranges::borrowed_range<Middle>);
  static_assert(std::ranges::sized_range<Middle>);
  static_assert(std::is_same_v<
                Middle,
                std::ranges::subrange<
                    decltype(values.begin()),
                    decltype(values.end()),
                    std::ranges::subrange_kind::sized>>);

  EXPECT_EQ(middle.begin(), values.begin() + 1);
  EXPECT_EQ(middle.end(), values.end() - 1);
  EXPECT_EQ(middle.size(), 3U);
  EXPECT_EQ(std::vector<int>(middle.begin(), middle.end()),
            (std::vector<int>{2, 3, 4}));

  // 当 iterator/sentinel 满足 sized_sentinel_for 时，CTAD 选择 sized subrange；对象只
  // 保存边界（必要时另存 size），销毁它不会销毁或延长 values。
}

TEST(Subrange, ExplicitSizedKindCanStoreSizeForAnUnsizedSentinel) {
  int values[] = {2, 3, 5, 7};
  using StoredSized = std::ranges::subrange<
      int*,
      PointerSentinel,
      std::ranges::subrange_kind::sized>;
  StoredSized first_three{values, PointerSentinel{values + 3}, 3};

  static_assert(!std::sized_sentinel_for<PointerSentinel, int*>);
  static_assert(std::ranges::sized_range<StoredSized>);
  EXPECT_EQ(first_three.size(), 3U);
  EXPECT_EQ(std::ranges::distance(first_three), 3);

  // sentinel 本身不能相减时，sized kind 构造函数接收显式 n 并在 subrange 内保存。
  // 调用者必须保证 n 与真实可达距离一致；类型系统无法验证这份冗余信息。
}

TEST(Subrange, TupleInterfaceSupportsStructuredBindingsOfTheTwoBoundaries) {
  int values[] = {1, 2, 3};
  auto range = std::ranges::subrange(values, values + 3);
  auto [first, last] = range;

  static_assert(std::tuple_size_v<decltype(range)> == 2);
  static_assert(std::is_same_v<
                std::tuple_element_t<0, decltype(range)>,
                int*>);
  EXPECT_EQ(first, values);
  EXPECT_EQ(last, values + 3);
  EXPECT_EQ(std::get<0>(range), values);

  // subrange 的 tuple_size 固定为 2，get<0>/get<1> 分别返回 iterator 与 sentinel；
  // 显式 size（若存在）不作为第三个结构化绑定元素。
}

TEST(Subrange, AdvanceMutatesWhileNextAndPrevReturnAdjustedCopies) {
  std::array<int, 5> values{1, 2, 3, 4, 5};
  auto range = std::ranges::subrange(values.begin(), values.end());

  auto dropped_two = range.next(2);
  auto restored_one = dropped_two.prev(1);

  EXPECT_EQ(*range.begin(), 1);
  EXPECT_EQ(*dropped_two.begin(), 3);
  EXPECT_EQ(*restored_one.begin(), 2);
  EXPECT_EQ(dropped_two.size(), 3U);

  range.advance(4);
  EXPECT_EQ(*range.begin(), 5);
  EXPECT_EQ(range.size(), 1U);

  // advance 改变 begin 并同步维护已存 size；next/prev 在副本上调用 advance。
  // 负向移动要求 bidirectional iterator，并且所有移动都必须留在合法可达范围内。
}

TEST(BorrowedAliases, TheyTurnUnsafeTemporaryResultsIntoDanglingTypes) {
  using LvalueIterator = std::ranges::borrowed_iterator_t<std::vector<int>&>;
  using TemporaryIterator = std::ranges::borrowed_iterator_t<std::vector<int>>;
  using TemporarySubrange = std::ranges::borrowed_subrange_t<std::vector<int>>;

  static_assert(std::is_same_v<LvalueIterator, std::vector<int>::iterator>);
  static_assert(std::is_same_v<TemporaryIterator, std::ranges::dangling>);
  static_assert(std::is_same_v<TemporarySubrange, std::ranges::dangling>);
  SUCCEED();

  // borrowed_* aliases 让泛型返回类型在安全时保留 iterator/subrange，不安全的临时
  // owning range 则变成不可解引用的 dangling 标记，阻止误用悬空结果。
}

TEST(Dangling, RangeAlgorithmsReturnTheMarkerForTemporaryOwnedRanges) {
  std::vector<int> values{1, 2, 3};
  auto safe = std::ranges::find(values, 2);
  auto unsafe = std::ranges::find(std::vector<int>{1, 2, 3}, 2);

  static_assert(std::is_same_v<decltype(safe), std::vector<int>::iterator>);
  static_assert(std::is_same_v<decltype(unsafe), std::ranges::dangling>);
  EXPECT_EQ(*safe, 2);
  (void)unsafe;

  // 算法仍会完整搜索临时 vector，但返回 dangling 而不是已失效 iterator。若只需 bool、
  // count 或复制出的值可直接消费临时 range；需要位置时应先把 owning range 命名。
}

}  // namespace
