// 排序稳定性与自定义次序。
// 共同问题：默认顺序是什么；排序是否稳定；key/comparator 调用模型如何；
// 排序是原地操作还是返回副本。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/cpp/standard_library/10_algorithms/
// polyglot-related+: test_094_sort_stability_partial_sort_nth_element_and_order_checks.cpp

#include <gtest/gtest.h>

#include <algorithm>
#include <string>
#include <vector>

namespace {

struct Record {
  std::string id;
  int group;
};

TEST(SortingConcept, SortMutatesTheSuppliedRange) {
  std::vector<int> values{3, 1, 2};

  std::sort(values.begin(), values.end());

  EXPECT_EQ(values, (std::vector<int>{1, 2, 3}));
}

TEST(SortingConcept, StableSortPreservesInputOrderWithinEqualKeys) {
  std::vector<Record> records{{"a", 1}, {"b", 0}, {"c", 1}};

  std::stable_sort(records.begin(), records.end(), [](const Record& left, const Record& right) {
    return left.group < right.group;
  });

  EXPECT_EQ(records[0].id, "b");
  EXPECT_EQ(records[1].id, "a");
  EXPECT_EQ(records[2].id, "c");
}

TEST(SortingConcept, SortDoesNotPromiseStability) {
  std::vector<Record> records{{"a", 1}, {"b", 0}, {"c", 1}};

  std::sort(records.begin(), records.end(), [](const Record& left, const Record& right) {
    return left.group < right.group;
  });

  EXPECT_EQ(records.front().id, "b");
  // 同组 a/c 的相对次序未指定；需要稳定性时必须选择 stable_sort。
}

TEST(SortingConcept, ComparatorMustExpressStrictWeakOrdering) {
  std::vector<int> values{1, 3, 2};
  auto descending = [](int left, int right) { return left > right; };

  std::sort(values.begin(), values.end(), descending);

  EXPECT_EQ(values, (std::vector<int>{3, 2, 1}));
  // comparator 返回 true 表示“排在之前”，不是 JavaScript 那样的负数/零/正数协议。
}

}  // namespace
