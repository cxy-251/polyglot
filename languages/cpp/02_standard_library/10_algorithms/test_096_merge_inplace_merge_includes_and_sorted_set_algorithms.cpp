// polyglot-covers:
// - cpp.stdlib.algorithms.merge-two-sorted-ranges-and-result-object
// - cpp.stdlib.algorithms.merge-stability-and-equivalent-input-order
// - cpp.stdlib.algorithms.inplace-merge-adjacent-sorted-halves
// - cpp.stdlib.algorithms.includes-sorted-multiset-containment
// - cpp.stdlib.algorithms.set-union-maximum-multiplicity
// - cpp.stdlib.algorithms.set-intersection-minimum-multiplicity
// - cpp.stdlib.algorithms.set-difference-subtracted-multiplicity
// - cpp.stdlib.algorithms.set-symmetric-difference-absolute-multiplicity
// - cpp.stdlib.algorithms.ranges-set-operation-result-positions
// - cpp.stdlib.algorithms.sorted-input-and-output-overlap-preconditions

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <functional>
#include <iterator>
#include <ranges>
#include <string>
#include <vector>

namespace {

TEST(Merge, RangesResultReportsBothConsumedInputsAndOutputEnd) {
  const std::array<int, 4> odds{1, 3, 5, 7};
  const std::array<int, 3> evens{2, 4, 6};
  std::array<int, 7> merged{};

  auto result = std::ranges::merge(odds, evens, merged.begin());

  EXPECT_EQ(result.in1, odds.end());
  EXPECT_EQ(result.in2, evens.end());
  EXPECT_EQ(result.out, merged.end());
  EXPECT_EQ(merged, (std::array<int, 7>{1, 2, 3, 4, 5, 6, 7}));

  // merge 线性地合并两个已按同一 comparator 排序的 range；输出容量必须足够容纳两者
  // 总长度。结果对象便于接着消费输入或从输出尾部继续写。
}

TEST(Merge, EquivalentItemsKeepStableOrderWithinAndAcrossInputs) {
  struct Entry {
    int key;
    char source;
    int sequence;
  };
  const std::vector<Entry> left{{1, 'L', 1}, {2, 'L', 2}, {2, 'L', 3}};
  const std::vector<Entry> right{{2, 'R', 1}, {2, 'R', 2}, {3, 'R', 3}};
  std::vector<Entry> merged;

  std::ranges::merge(
      left,
      right,
      std::back_inserter(merged),
      std::less<>{},
      &Entry::key,
      &Entry::key);

  ASSERT_EQ(merged.size(), 6U);
  EXPECT_EQ(merged[1].source, 'L');
  EXPECT_EQ(merged[1].sequence, 2);
  EXPECT_EQ(merged[2].source, 'L');
  EXPECT_EQ(merged[2].sequence, 3);
  EXPECT_EQ(merged[3].source, 'R');
  EXPECT_EQ(merged[4].source, 'R');

  // merge 是稳定的：各输入内部相对顺序保持；两路元素等价时，第一输入的元素排在第二
  // 输入等价元素之前。两路 projection 可以不同，但必须导向同一个 strict weak order。
}

TEST(Merge, DescendingInputsRequireTheSameDescendingComparator) {
  const std::array<int, 3> first{9, 5, 1};
  const std::array<int, 4> second{8, 6, 4, 2};
  std::vector<int> output;

  std::ranges::merge(
      first, second, std::back_inserter(output), std::greater<>{});

  EXPECT_EQ(output, (std::vector<int>{9, 8, 6, 5, 4, 2, 1}));

  // 输入若按 greater 排列却用默认 less，不满足前置条件；算法不会先检查或修复排序。
}

TEST(InplaceMerge, ItMergesTwoAdjacentSortedHalvesInsideOneRange) {
  std::vector<int> values{1, 4, 7, 9, 2, 3, 8, 10};
  auto middle = values.begin() + 4;

  std::inplace_merge(values.begin(), middle, values.end());

  EXPECT_EQ(values, (std::vector<int>{1, 2, 3, 4, 7, 8, 9, 10}));

  // 前置条件是 `[first,middle)` 与 `[middle,last)` 各自已排序且相邻；整个范围原先无需
  // 有序。算法原地给出稳定合并结果，实现可能为加速申请临时缓冲区。
}

TEST(InplaceMerge, ProjectionPreservesEquivalentRecordOrder) {
  struct Row {
    int key;
    char id;
  };
  std::vector<Row> rows{{1, 'a'}, {2, 'b'}, {2, 'c'}, {2, 'd'}, {3, 'e'}};

  std::ranges::inplace_merge(rows, rows.begin() + 3, std::less<>{}, &Row::key);

  EXPECT_EQ(rows[0].id, 'a');
  EXPECT_EQ(rows[1].id, 'b');
  EXPECT_EQ(rows[2].id, 'c');
  EXPECT_EQ(rows[3].id, 'd');
  EXPECT_EQ(rows[4].id, 'e');

  // 左半的等价项 b、c 保持顺序，并排在右半等价项 d 之前。
}

TEST(Includes, ItChecksMultisetContainmentIncludingDuplicateCounts) {
  const std::array<int, 7> superset{1, 2, 2, 2, 4, 5, 8};
  const std::array<int, 3> present{2, 2, 5};
  const std::array<int, 4> too_many_twos{2, 2, 2, 2};

  EXPECT_TRUE(std::ranges::includes(superset, present));
  EXPECT_FALSE(std::ranges::includes(superset, too_many_twos));

  // includes 按有序多重集合判断包含关系：第二路中某值出现 n 次，第一路至少需要 n 次。
  // 空第二路总被包含，未排序输入不满足前置条件。
}

TEST(Includes, ProjectionsCanCompareDifferentRecordShapesByACommonKey) {
  struct Inventory {
    int sku;
    int stock;
  };
  struct Request {
    int sku;
  };
  const std::vector<Inventory> inventory{{10, 5}, {20, 3}, {30, 8}};
  const std::vector<Request> request{{10}, {30}};

  EXPECT_TRUE(std::ranges::includes(
      inventory,
      request,
      std::less<>{},
      &Inventory::sku,
      &Request::sku));

  // includes 这里只比较 sku 是否存在；stock 数量是业务字段，不会自动参与多重性判断。
}

TEST(SetUnion, DuplicateMultiplicityIsTheMaximumFromEitherInput) {
  const std::array<int, 6> first{1, 2, 2, 2, 4, 7};
  const std::array<int, 6> second{2, 2, 3, 4, 4, 8};
  std::vector<int> output;

  std::ranges::set_union(first, second, std::back_inserter(output));

  EXPECT_EQ(output, (std::vector<int>{1, 2, 2, 2, 3, 4, 4, 7, 8}));

  // 某值在两路出现 m、n 次时，union 输出 max(m,n) 次，不是“只留一个”的去重集合。
}

TEST(SetIntersection, DuplicateMultiplicityIsTheMinimumFromBothInputs) {
  const std::array<int, 6> first{1, 2, 2, 2, 4, 7};
  const std::array<int, 6> second{2, 2, 3, 4, 4, 8};
  std::vector<int> output;

  auto result = std::ranges::set_intersection(
      first, second, std::back_inserter(output));

  EXPECT_EQ(output, (std::vector<int>{2, 2, 4}));
  EXPECT_EQ(result.in1, first.end());
  EXPECT_EQ(result.in2, second.end());

  // intersection 输出 min(m,n) 次。实现可能在一侧耗尽后停止比较，但 ranges 结果会把
  // 输入位置推进到规定的最终位置，输出位置可继续使用。
}

TEST(SetDifference, ItSubtractsSecondMultiplicityFromTheFirst) {
  const std::array<int, 7> first{1, 2, 2, 2, 4, 4, 7};
  const std::array<int, 4> second{2, 2, 4, 8};
  std::vector<int> output;

  std::ranges::set_difference(first, second, std::back_inserter(output));

  EXPECT_EQ(output, (std::vector<int>{1, 2, 4, 7}));

  // first 中 m 次减去 second 中 n 次，输出 max(m-n,0) 次；方向不可交换。
}

TEST(SetSymmetricDifference, ItKeepsTheAbsoluteMultiplicityDifference) {
  const std::array<int, 7> first{1, 2, 2, 2, 4, 4, 7};
  const std::array<int, 6> second{2, 2, 3, 4, 8, 8};
  std::vector<int> output;

  auto result = std::ranges::set_symmetric_difference(
      first, second, std::back_inserter(output));

  EXPECT_EQ(output, (std::vector<int>{1, 2, 3, 4, 7, 8, 8}));
  EXPECT_EQ(result.in1, first.end());
  EXPECT_EQ(result.in2, second.end());

  // 对每个等价类输出 abs(m-n) 次，相当于保留只在一边多出来的份数。
}

TEST(SetAlgorithms, EmptyInputsExposeTheIdentityCases) {
  const std::vector<int> empty;
  const std::vector<int> values{1, 2, 2, 3};
  std::vector<int> union_output;
  std::vector<int> intersection_output;

  std::ranges::set_union(
      empty, values, std::back_inserter(union_output));
  std::ranges::set_intersection(
      empty, values, std::back_inserter(intersection_output));

  EXPECT_EQ(union_output, values);
  EXPECT_TRUE(intersection_output.empty());
}

TEST(SetAlgorithms, OutputMustNotOverwriteUnreadInput) {
  const std::array<int, 3> first{1, 3, 5};
  const std::array<int, 3> second{2, 4, 6};
  std::array<int, 6> output{};

  auto result = std::ranges::set_union(first, second, output.begin());

  EXPECT_EQ(result.out, output.end());
  EXPECT_EQ(output, (std::array<int, 6>{1, 2, 3, 4, 5, 6}));

  // merge 与 set 输出算法要求目标不以会覆盖未读元素的方式和输入重叠。想在一个容器中
  // 合并相邻已排序段应使用 inplace_merge，而不是把 merge 输出指回源范围。
}

}  // namespace
