// 序列修改与失效。
// 共同问题：修改容器后迭代器和视图是否仍有效；遍历期间修改会发生什么；
// 哪些结构能检测不安全的结构变化。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/cpp/language/test_011_object_lifetime_references_and_storage_reuse.cpp

#include <gtest/gtest.h>

#include <list>
#include <vector>

namespace {

TEST(MutationInvalidationConcept, VectorReallocationChangesStorageIdentity) {
  std::vector<int> values;
  values.reserve(1);
  values.push_back(1);
  const int* old_storage = values.data();

  values.push_back(2);

  EXPECT_NE(values.data(), old_storage);
  EXPECT_EQ(values, (std::vector<int>{1, 2}));

  // 重分配后旧 iterator/reference/pointer 失效；只比较地址，不解引用旧指针。
}

TEST(MutationInvalidationConcept, ReserveCanKeepReferencesValidUntilCapacityIsExceeded) {
  std::vector<int> values;
  values.reserve(3);
  values.push_back(1);
  int* first = &values[0];

  values.push_back(2);

  EXPECT_EQ(first, &values[0]);
  EXPECT_EQ(*first, 1);
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
