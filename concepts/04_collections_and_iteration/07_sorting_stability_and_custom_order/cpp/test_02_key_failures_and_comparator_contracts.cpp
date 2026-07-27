// 排序回调、失败与次序契约。
// 共同问题：排序回调可能调用多少次；回调失败时输入是否改变；
// 不一致的次序关系是否由运行时修复。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/cpp/standard_library/10_algorithms/
// polyglot-related+: test_094_sort_stability_partial_sort_nth_element_and_order_checks.cpp
// polyglot-related: languages/cpp/standard_library/08_iterators/
// polyglot-related+: test_079_indirect_callable_projected_and_algorithm_requirement_concepts.cpp

#include <gtest/gtest.h>

#include <algorithm>
#include <ranges>
#include <string>
#include <vector>

namespace {

struct Record {
  std::string id;
  int rank;
};

TEST(SortCallbackConcept, ProjectionRunsAsPartOfComparison) {
  std::vector<Record> records{{"three", 3}, {"one", 1}, {"two", 2}};
  int projection_calls = 0;

  std::ranges::sort(
      records,
      std::ranges::less{},
      [&projection_calls](const Record& record) {
        ++projection_calls;
        return record.rank;
      });

  EXPECT_EQ(records[0].id, "one");
  EXPECT_EQ(records[1].id, "two");
  EXPECT_EQ(records[2].id, "three");
  EXPECT_GT(projection_calls, 0);

  // 与 Python key 的一次性装饰不同，C++ projection 可随比较重复求值；不得依赖精确
  // 调用次数或把有副作用的 projection 当作工作流。
}

TEST(SortCallbackConcept, FiniteProbeChecksAComparatorSampleWithoutClaimingProof) {
  const std::vector<int> values{1, 2, 3};
  const auto before = [](int left, int right) { return left < right; };

  for (int value : values) {
    EXPECT_FALSE(before(value, value));
  }
  for (int left : values) {
    for (int right : values) {
      if (before(left, right)) {
        EXPECT_FALSE(before(right, left));
      }
      for (int last : values) {
        if (before(left, right) && before(right, last)) {
          EXPECT_TRUE(before(left, last));
        }
      }
    }
  }

  // 这只检查有限样本。违反 strict weak ordering 会使标准排序算法的前置条件不成立；
  // 不执行故意矛盾的 comparator 来观察某个实现的偶然排列。
}

}  // namespace
