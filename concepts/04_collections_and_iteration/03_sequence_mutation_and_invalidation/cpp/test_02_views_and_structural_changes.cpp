// 视图、复制与结构修改边界。
// 共同问题：派生对象是独立副本还是共享视图；哪些修改保持现有游标有效；
// 安全删除循环应基于什么稳定观察。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_063_array_and_span_fixed_storage_non_owning_views_and_bytes.cpp
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_064_vector_storage_capacity_insertion_erasure_and_invalidation.cpp

#include <gtest/gtest.h>

#include <span>
#include <vector>

namespace {

TEST(ViewMutationConcept, VectorCopyIsIndependentButSpanSharesStorage) {
  std::vector<int> values{1, 2, 3};
  std::vector<int> copied = values;
  std::span<int> view = values;

  copied[0] = 9;
  view[1] = 8;

  EXPECT_EQ(copied, (std::vector<int>{9, 2, 3}));
  EXPECT_EQ(values, (std::vector<int>{1, 8, 3}));
}

TEST(ViewMutationConcept, EraseKeepsIteratorsBeforeTheErasedPositionValid) {
  std::vector<int> values{1, 2, 3, 4};
  auto first = values.begin();
  auto erased = std::next(values.begin());

  auto successor = values.erase(erased);

  EXPECT_EQ(*first, 1);
  ASSERT_NE(successor, values.end());
  EXPECT_EQ(*successor, 3);
  EXPECT_EQ(values, (std::vector<int>{1, 3, 4}));

  // erase 使删除点及其后的旧 iterator/reference 失效，所以只使用删除点之前的 first
  // 和 erase 返回的新 successor；不读取旧 erased。
}

TEST(ViewMutationConcept, SpanLifetimeDependsOnTheUnderlyingStorage) {
  std::vector<int> values{1, 2};
  values.reserve(4);
  std::span<int> view = values;
  const std::size_t capacity = values.capacity();

  values.push_back(3);

  EXPECT_EQ(view[0], 1);
  EXPECT_EQ(view[1], 2);
  EXPECT_EQ(view.size(), 2U);
  EXPECT_EQ(values.capacity(), capacity);

  // 未重分配时原有元素地址稳定，旧 span 仍只保留创建时的长度 2；一旦 vector 重分配，
  // span 全部悬空。危险分支不能通过读取失效 view 来测试。
}

}  // namespace
