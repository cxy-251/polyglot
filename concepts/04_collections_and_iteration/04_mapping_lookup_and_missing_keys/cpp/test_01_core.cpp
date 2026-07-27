// 映射查找与缺失键。
// 共同问题：缺失查找返回值还是错误；读取是否可能插入；如何区分缺失与空值；
// 自定义映射能否提供默认策略。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: mapping_lookup_and_missing_keys
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_068_ordered_associative_lookup_map_insertion_nodes_and_multi_keys.cpp

#include <gtest/gtest.h>

#include <map>
#include <stdexcept>
#include <string>

namespace {

TEST(MappingLookupConcept, AtReportsMissingWithoutInserting) {
  std::map<std::string, int> mapping{{"answer", 42}};

  EXPECT_EQ(mapping.at("answer"), 42);
  EXPECT_THROW(static_cast<void>(mapping.at("missing")), std::out_of_range);
  EXPECT_EQ(mapping.size(), 1U);
}

TEST(MappingLookupConcept, SubscriptDefaultInsertsAMissingKey) {
  std::map<std::string, int> mapping;

  int value = mapping["missing"];

  EXPECT_EQ(value, 0);
  EXPECT_TRUE(mapping.contains("missing"));
  EXPECT_EQ(mapping.size(), 1U);
}

TEST(MappingLookupConcept, FindSeparatesPresenceFromTheMappedValue) {
  std::map<std::string, int> mapping{{"zero", 0}};

  auto present = mapping.find("zero");
  auto missing = mapping.find("missing");

  ASSERT_NE(present, mapping.end());
  EXPECT_EQ(present->second, 0);
  EXPECT_EQ(missing, mapping.end());
}

TEST(MappingLookupConcept, TryEmplaceBuildsOnlyWhenInsertionWins) {
  std::map<std::string, std::string> mapping{{"key", "old"}};

  auto [existing, inserted] = mapping.try_emplace("key", "new");
  auto [created, created_now] = mapping.try_emplace("other", "value");

  EXPECT_FALSE(inserted);
  EXPECT_EQ(existing->second, "old");
  EXPECT_TRUE(created_now);
  EXPECT_EQ(created->second, "value");
}

}  // namespace
