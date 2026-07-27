// 集合成员、去重与运算。
// 共同问题：集合使用哪种相等关系；是否保持顺序；如何表达集合运算；
// 可变集合能否作为另一个集合的成员。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: sets_membership_and_deduplication
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_069_unordered_associative_hash_policy_buckets_invalidation_and_multi_keys.cpp
// polyglot-related: languages/cpp/standard_library/10_algorithms/
// polyglot-related+: test_096_merge_inplace_merge_includes_and_sorted_set_algorithms.cpp

#include <gtest/gtest.h>

#include <algorithm>
#include <iterator>
#include <set>
#include <unordered_set>
#include <vector>

namespace {

TEST(SetSemanticsConcept, OrderedSetDeduplicatesByComparatorEquivalence) {
  std::set<int> values{3, 1, 1, 2};

  EXPECT_EQ(values.size(), 3U);
  EXPECT_EQ(std::vector<int>(values.begin(), values.end()), (std::vector<int>{1, 2, 3}));
}

TEST(SetSemanticsConcept, UnorderedSetUsesHashAndEqualityWithoutOrderPromise) {
  std::unordered_set<int> values{1, 1, 2};

  EXPECT_EQ(values.size(), 2U);
  EXPECT_TRUE(values.contains(1));
  EXPECT_TRUE(values.contains(2));

  // 迭代次序不是插入顺序；不能像 JavaScript Set 那样依赖稳定插入顺序。
}

TEST(SetSemanticsConcept, SetAlgorithmsWriteResultsThroughAnOutputIterator) {
  std::set<int> left{1, 2};
  std::set<int> right{2, 3};
  std::vector<int> result;

  std::set_union(
      left.begin(),
      left.end(),
      right.begin(),
      right.end(),
      std::back_inserter(result));

  EXPECT_EQ(result, (std::vector<int>{1, 2, 3}));
}

TEST(SetSemanticsConcept, CustomHashAndEqualityDefineKeyIdentity) {
  struct Key {
    int value;
    bool operator==(const Key&) const = default;
  };
  struct Hash {
    std::size_t operator()(const Key& key) const { return std::hash<int>{}(key.value); }
  };

  std::unordered_set<Key, Hash> values{{1}, {1}};
  EXPECT_EQ(values.size(), 1U);
}

}  // namespace
