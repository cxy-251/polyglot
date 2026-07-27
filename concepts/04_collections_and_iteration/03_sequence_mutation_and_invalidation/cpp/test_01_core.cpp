// 序列修改与失效。
// 共同问题：修改容器后迭代器和视图是否仍有效；遍历期间修改会发生什么；
// 哪些结构能检测不安全的结构变化。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/cpp/language/test_011_object_lifetime_references_and_storage_reuse.cpp

#include <gtest/gtest.h>

#include <algorithm>
#include <list>
#include <vector>

namespace {

TEST(MutationInvalidationConcept, InsertingPastCapacityForcesReallocation) {
  std::vector<int> values{1};
  values.reserve(4);
  const std::size_t original_capacity = values.capacity();

  while (values.size() < original_capacity) {
    values.push_back(static_cast<int>(values.size() + 1));
  }
  const std::vector<int> original_values = values;

  values.push_back(99);

  EXPECT_GT(values.capacity(), original_capacity);
  EXPECT_TRUE(std::equal(original_values.begin(), original_values.end(), values.begin()));
  EXPECT_EQ(values.back(), 99);

  // size 已等于真实 capacity，下一次插入按标准保证触发重分配；旧 iterator、引用和指针
  // 全部失效，因此测试只观察新容器的 capacity 与值，不读取或比较任何悬空句柄。
}

TEST(MutationInvalidationConcept, ReserveCanKeepReferencesValidUntilCapacityIsExceeded) {
  std::vector<int> values;
  values.reserve(3);
  values.push_back(1);
  int* first = &values[0];
  const std::size_t capacity = values.capacity();

  while (values.size() < capacity) {
    values.push_back(static_cast<int>(values.size() + 1));
  }

  EXPECT_EQ(first, &values[0]);
  EXPECT_EQ(*first, 1);
  EXPECT_EQ(values.capacity(), capacity);
}

TEST(MutationInvalidationConcept, ListInsertionPreservesExistingIterators) {
  std::list<int> values{1, 3};
  auto first = values.begin();

  values.insert(std::next(first), 2);

  EXPECT_EQ(*first, 1);
  EXPECT_EQ(values, (std::list<int>{1, 2, 3}));
}

TEST(MutationInvalidationConcept, EraseLoopUsesReturnedSuccessor) {
  std::vector<int> values{1, 2, 3, 4};

  for (auto iterator = values.begin(); iterator != values.end();) {
    if (*iterator % 2 != 0) {
      iterator = values.erase(iterator);
    } else {
      ++iterator;
    }
  }

  EXPECT_EQ(values, (std::vector<int>{2, 4}));
}

}  // namespace
