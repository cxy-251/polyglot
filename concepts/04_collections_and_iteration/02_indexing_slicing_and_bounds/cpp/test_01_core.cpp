// 索引、切片与边界。
// 共同问题：负索引如何解释；切片是否复制；越界如何报告；
// 自定义类型通过什么入口接收索引与切片。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: indexing_slicing_and_bounds
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_063_array_and_span_fixed_storage_non_owning_views_and_bytes.cpp
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_064_vector_storage_capacity_insertion_erasure_and_invalidation.cpp

#include <gtest/gtest.h>

#include <span>
#include <stdexcept>
#include <vector>

namespace {

TEST(IndexingConcept, VectorIndexUsesUnsignedPositionWithoutNegativeIndexing) {
  std::vector<int> values{10, 20, 30};

  EXPECT_EQ(values[0], 10);
  EXPECT_EQ(values[values.size() - 1], 30);

  // 把 -1 转成 size_t 会得到巨大正数；C++ 容器没有 Python/Array.at 式负索引。
}

TEST(IndexingConcept, AtChecksBoundsWhileSubscriptRequiresValidIndex) {
  std::vector<int> values{10, 20};

  EXPECT_EQ(values.at(1), 20);
  EXPECT_THROW(static_cast<void>(values.at(2)), std::out_of_range);

  // values[2] 越界是未定义行为，不能用执行结果证明。
}

TEST(IndexingConcept, SpanSubspanCreatesANonOwningView) {
  std::vector<int> values{0, 1, 2, 3};
  std::span<int> view = values;
  auto middle = view.subspan(1, 2);

  middle[0] = 9;

  EXPECT_EQ(values, (std::vector<int>{0, 9, 2, 3}));
  EXPECT_EQ(middle.size(), 2U);
}

TEST(IndexingConcept, CustomSubscriptDefinesOnlyTheOperationsItProvides) {
  struct Pair {
    int values[2];
    int& operator[](std::size_t index) { return values[index]; }
  };
  Pair pair{{1, 2}};

  pair[1] = 9;
  EXPECT_EQ(pair.values[1], 9);

  // 标准语法不携带 slice 对象；范围视图通常用 iterator、span 或 ranges 组合表达。
}

}  // namespace
