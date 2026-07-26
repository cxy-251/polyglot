// polyglot-covers:
// - cpp.stdlib.algorithms.lower-bound-first-not-less-and-insertion-point
// - cpp.stdlib.algorithms.upper-bound-first-greater
// - cpp.stdlib.algorithms.equal-range-duplicate-subrange
// - cpp.stdlib.algorithms.binary-search-membership-without-position
// - cpp.stdlib.algorithms.binary-search-comparator-consistency-precondition
// - cpp.stdlib.algorithms.ranges-bounds-projection
// - cpp.stdlib.algorithms.descending-order-bound-search
// - cpp.stdlib.algorithms.heterogeneous-bound-search
// - cpp.stdlib.algorithms.bound-search-forward-iterator-complexity
// - cpp.stdlib.algorithms.sorted-insertion-workflow

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <functional>
#include <iterator>
#include <ranges>
#include <string>
#include <string_view>
#include <vector>

namespace {

TEST(LowerBound, ItReturnsTheFirstElementNotOrderedBeforeTheValue) {
  const std::array<int, 7> values{1, 2, 2, 2, 4, 6, 8};

  auto first_two = std::lower_bound(values.begin(), values.end(), 2);
  auto insertion_for_five = std::lower_bound(values.begin(), values.end(), 5);
  auto after_all = std::lower_bound(values.begin(), values.end(), 9);

  EXPECT_EQ(first_two, values.begin() + 1);
  EXPECT_EQ(insertion_for_five, values.begin() + 5);
  EXPECT_EQ(after_all, values.end());

  // 默认升序下，lower_bound 找第一个 `element < value` 为 false 的位置；该位置既是
  // 第一个等价值，也是不存在时维持有序性的插入点。
}

TEST(UpperBound, ItReturnsTheFirstElementOrderedAfterTheValue) {
  const std::array<int, 7> values{1, 2, 2, 2, 4, 6, 8};

  auto after_twos = std::upper_bound(values.begin(), values.end(), 2);
  auto before_first = std::upper_bound(values.begin(), values.end(), 0);

  EXPECT_EQ(after_twos, values.begin() + 4);
  EXPECT_EQ(before_first, values.begin());

  // upper_bound 找第一个 `value < element` 为 true 的位置，因此插在这里会排在所有
  // 等价值之后；它和 lower_bound 对 comparator 参数的调用方向不同。
}

TEST(EqualRange, ItReturnsExactlyTheHalfOpenDuplicateRun) {
  const std::vector<int> values{1, 2, 2, 2, 4, 6, 8};

  auto matches = std::ranges::equal_range(values, 2);

  EXPECT_EQ(matches.begin(), values.begin() + 1);
  EXPECT_EQ(matches.end(), values.begin() + 4);
  EXPECT_EQ(std::vector<int>(matches.begin(), matches.end()),
            (std::vector<int>{2, 2, 2}));

  // equal_range 等价于同一顺序关系下的 `[lower_bound,upper_bound)`；返回空 subrange
  // 表示未找到，并且这个空位置仍是合法插入点。
}

TEST(EqualRange, MissingValueProducesAnEmptyRangeAtItsInsertionPoint) {
  const std::array<int, 5> values{1, 3, 5, 7, 9};

  auto missing = std::ranges::equal_range(values, 6);

  EXPECT_EQ(missing.begin(), values.begin() + 3);
  EXPECT_EQ(missing.end(), values.begin() + 3);
  EXPECT_TRUE(missing.empty());
}

TEST(BinarySearch, ItAnswersMembershipButDoesNotExposeTheMatchingPosition) {
  const std::array<int, 6> values{1, 3, 3, 5, 7, 9};

  EXPECT_TRUE(std::ranges::binary_search(values, 3));
  EXPECT_FALSE(std::ranges::binary_search(values, 4));

  // binary_search 只返回 bool；需要 iterator、重复数量或插入位置时直接用 lower_bound
  // 或 equal_range，没必要先 binary_search 再做第二次查询。
}

TEST(BinarySearch, QueryMustUseTheSameOrderingThatStructuresTheRange) {
  const std::array<int, 5> descending{9, 7, 5, 3, 1};

  EXPECT_TRUE(std::ranges::binary_search(descending, 5, std::greater<>{}));
  auto place_for_six = std::ranges::lower_bound(
      descending, 6, std::greater<>{});

  EXPECT_EQ(place_for_six, descending.begin() + 2);

  // 对 descending 却使用默认 less 不满足“按该 comparator 已分区”的前置条件，结果
  // 不是可靠的 false 或某个任意位置。比较器也必须是 strict weak ordering。
}

TEST(RangesBounds, ProjectionSearchesARecordKeyWithoutTemporaryRecords) {
  struct User {
    int id;
    std::string name;
  };
  const std::vector<User> users{{10, "Ada"}, {20, "Bjarne"}, {20, "Linus"}, {40, "Grace"}};

  auto first_twenty = std::ranges::lower_bound(
      users, 20, std::less<>{}, &User::id);
  auto twenties = std::ranges::equal_range(
      users, 20, std::less<>{}, &User::id);

  ASSERT_NE(first_twenty, users.end());
  EXPECT_EQ(first_twenty->name, "Bjarne");
  EXPECT_EQ(twenties.begin(), users.begin() + 1);
  EXPECT_EQ(twenties.end(), users.begin() + 3);

  // projection 参与排序和查询的每次比较；范围必须已经按相同 `less(project(item))`
  // 关系组织。只按其他字段排序后再投影 id 查询会破坏前置条件。
}

struct NamedValue {
  std::string name;
  int payload;
};

struct NameLess {
  using is_transparent = void;

  bool operator()(const NamedValue& left, std::string_view right) const {
    return left.name < right;
  }

  bool operator()(std::string_view left, const NamedValue& right) const {
    return left < right.name;
  }

  bool operator()(const NamedValue& left, const NamedValue& right) const {
    return left.name < right.name;
  }
};

TEST(HeterogeneousSearch, TransparentComparisonAvoidsConstructingARecordKey) {
  const std::vector<NamedValue> values{{"alpha", 1}, {"beta", 2}, {"gamma", 3}};

  auto lower = std::lower_bound(
      values.begin(), values.end(), std::string_view{"beta"}, NameLess{});
  auto upper = std::upper_bound(
      values.begin(), values.end(), std::string_view{"beta"}, NameLess{});

  ASSERT_NE(lower, values.end());
  EXPECT_EQ(lower->payload, 2);
  EXPECT_EQ(upper, values.begin() + 2);

  // lower_bound 会调用 comp(element,value)，upper_bound 会调用 comp(value,element)；
  // 支持完整 bounds 家族的异构 comparator 应提供两种方向，并保持同一顺序关系。
}

TEST(SortedInsertion, LowerAndUpperBoundChooseOppositeSidesOfEquivalentItems) {
  struct Entry {
    int key;
    char tag;
  };
  std::vector<Entry> entries{{1, 'a'}, {2, 'b'}, {2, 'c'}, {4, 'd'}};

  auto before_equals = std::ranges::lower_bound(
      entries, 2, std::less<>{}, &Entry::key);
  entries.insert(before_equals, Entry{2, 'x'});

  auto after_equals = std::ranges::upper_bound(
      entries, 2, std::less<>{}, &Entry::key);
  entries.insert(after_equals, Entry{2, 'y'});

  EXPECT_EQ(entries[1].tag, 'x');
  EXPECT_EQ(entries[2].tag, 'b');
  EXPECT_EQ(entries[3].tag, 'c');
  EXPECT_EQ(entries[4].tag, 'y');

  // vector::insert 可能重分配，所以第一次查询得到的 iterator 在 insert 后不能复用；
  // 第二个边界必须重新查询。lower 放在等价组前，upper 放在等价组后。
}

TEST(BoundSearch, EmptyAndExtremeQueriesReturnValidBoundaries) {
  const std::vector<int> empty;
  const std::array<int, 3> values{10, 20, 30};

  EXPECT_EQ(std::ranges::lower_bound(empty, 5), empty.end());
  EXPECT_EQ(std::ranges::lower_bound(values, 0), values.begin());
  EXPECT_EQ(std::ranges::upper_bound(values, 30), values.end());

  // 返回 begin/end 是正常边界，不应在未检查 end 时直接解引用查询结果。
}

TEST(BoundComplexity, ForwardIteratorsStillHaveLinearNavigationCost) {
  const std::array<int, 8> values{1, 2, 3, 4, 5, 6, 7, 8};
  auto found = std::lower_bound(values.begin(), values.end(), 6);

  EXPECT_EQ(found, values.begin() + 5);

  // 标准将比较次数限制为对数级，但只要求 ForwardIterator；对非随机访问 iterator，
  // std::advance 造成的 iterator 增量总数可能是线性。关联容器应优先用成员 lower_bound，
  // 它能利用树结构，而不是把通用算法套在树 iterator 上。
}

}  // namespace
