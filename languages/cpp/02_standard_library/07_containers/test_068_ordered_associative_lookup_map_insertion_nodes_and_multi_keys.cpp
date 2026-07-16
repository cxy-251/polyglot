// polyglot-covers:
// - cpp.stdlib.containers.ordered-associative-strict-weak-order-and-equivalence
// - cpp.stdlib.containers.set-insert-contains-find-and-erase
// - cpp.stdlib.containers.ordered-lower-upper-bound-and-equal-range
// - cpp.stdlib.containers.map-key-constness-and-mapped-mutability
// - cpp.stdlib.containers.map-subscript-at-and-default-insertion
// - cpp.stdlib.containers.map-try-emplace-and-insert-or-assign
// - cpp.stdlib.containers.transparent-comparator-heterogeneous-lookup
// - cpp.stdlib.containers.node-handle-extract-mutate-and-conflict
// - cpp.stdlib.containers.associative-merge-and-duplicate-retention
// - cpp.stdlib.containers.multiset-and-multimap-equivalent-key-ranges
// - cpp.stdlib.containers.ordered-associative-erase-if

#include <gtest/gtest.h>

#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct LastDigitLess {
  bool operator()(int left, int right) const {
    return left % 10 < right % 10;
  }
};

TEST(OrderedAssociative, ComparatorEquivalenceDeterminesKeyUniqueness) {
  std::set<int, LastDigitLess> values;

  const auto [twelve, inserted_twelve] = values.insert(12);
  const auto [twenty_two, inserted_twenty_two] = values.insert(22);
  const auto [thirteen, inserted_thirteen] = values.insert(13);

  EXPECT_TRUE(inserted_twelve);
  EXPECT_FALSE(inserted_twenty_two);
  EXPECT_TRUE(inserted_thirteen);
  EXPECT_EQ(*twelve, 12);
  EXPECT_EQ(twenty_two, twelve);
  EXPECT_EQ(*thirteen, 13);
  EXPECT_EQ(values.size(), 2U);

  // 唯一性不是由 operator== 决定，而是 `!comp(a,b) && !comp(b,a)` 的等价关系。
  // 此比较器只看个位，12 与 22 因而是同一个 key。比较器必须满足严格弱序。
}

TEST(Set, InsertFindContainsAndEraseExposeWhetherAUniqueKeyExists) {
  std::set<std::string> names{"Ada", "Grace"};

  auto [position, inserted] = names.emplace("Bjarne");
  auto [same_position, duplicate] = names.insert("Bjarne");

  EXPECT_TRUE(inserted);
  EXPECT_FALSE(duplicate);
  EXPECT_EQ(position, same_position);
  EXPECT_TRUE(names.contains("Ada"));
  EXPECT_EQ(names.find("missing"), names.end());

  const auto removed = names.erase("Grace");
  EXPECT_EQ(removed, 1U);
  EXPECT_FALSE(names.contains("Grace"));

  // unique set 的 insert/emplace 返回 iterator 与是否插入的 bool；重复 key 不替换旧值。
  // erase(key) 返回实际删除数量，因唯一键只能为 0 或 1。
}

TEST(OrderedAssociative, BoundsDescribeOneComparatorEquivalentRange) {
  std::multiset<int> values{1, 2, 2, 2, 4, 5};

  auto lower = values.lower_bound(2);
  auto upper = values.upper_bound(2);
  auto [same_lower, same_upper] = values.equal_range(2);

  ASSERT_NE(lower, values.end());
  ASSERT_NE(upper, values.end());
  EXPECT_EQ(*lower, 2);
  EXPECT_EQ(*upper, 4);
  EXPECT_EQ(lower, same_lower);
  EXPECT_EQ(upper, same_upper);
  EXPECT_EQ(std::distance(lower, upper), 3);

  // lower_bound 是首个“不小于 key”的位置，upper_bound 是首个“大于 key”的位置；
  // equal_range 同时返回两者。判断依据始终是 comparator，而不是数值运算符的名字。
}

TEST(Map, KeysAreConstInsideNodesWhileMappedValuesRemainMutable) {
  std::map<std::string, int> scores{{"Ada", 10}, {"Bjarne", 20}};
  auto iterator = scores.begin();

  using EntryReference = decltype(*iterator);
  using Entry = std::remove_reference_t<EntryReference>;
  static_assert(std::is_const_v<typename Entry::first_type>);
  static_assert(!std::is_const_v<typename Entry::second_type>);

  iterator->second += 1;
  EXPECT_EQ(iterator->second, 11);

  // key 参与树的有序结构，原地修改会破坏不变量，所以 pair 的 first 是 const Key；
  // mapped value 不决定顺序，可以通过 iterator 修改。改 key 应使用 extract 的 node handle。
}

TEST(Map, SubscriptDefaultInsertsWhileAtOnlyChecksExistingKeys) {
  std::map<std::string, int> counts;

  EXPECT_EQ(counts["apple"], 0);
  counts["apple"] += 2;
  EXPECT_EQ(counts.at("apple"), 2);
  EXPECT_THROW((void)counts.at("pear"), std::out_of_range);
  EXPECT_FALSE(counts.contains("pear"));

  const auto before = counts.size();
  (void)counts["pear"];
  EXPECT_EQ(counts.size(), before + 1);

  // operator[] 在 key 不存在时插入 value-initialized mapped value，因此一次“读取”也会
  // 改变容器，并要求 mapped type 可按该路径构造。at() 不插入，缺失时抛 out_of_range。
}

TEST(Map, TryEmplaceDoesNotConsumeArgumentsWhenTheKeyAlreadyExists) {
  std::map<int, std::unique_ptr<int>> owners;
  auto [first, inserted] = owners.try_emplace(1, std::make_unique<int>(7));
  ASSERT_TRUE(inserted);
  EXPECT_EQ(*first->second, 7);

  auto candidate = std::make_unique<int>(11);
  auto [existing, duplicate] = owners.try_emplace(1, std::move(candidate));

  EXPECT_FALSE(duplicate);
  EXPECT_EQ(existing, first);
  ASSERT_NE(candidate, nullptr);
  EXPECT_EQ(*candidate, 11);
  EXPECT_EQ(*owners.at(1), 7);

  // try_emplace 只在 key 缺失时用参数构造 mapped value；重复 key 时不会移动 candidate。
  // 对 move-only 或构造昂贵的 mapped value，它比先造 pair 再 insert 更安全直接。
}

TEST(Map, InsertOrAssignDistinguishesInsertionFromReplacement) {
  std::map<std::string, int> scores{{"Ada", 10}};

  auto [ada, inserted_ada] = scores.insert_or_assign("Ada", 12);
  auto [grace, inserted_grace] = scores.insert_or_assign("Grace", 20);

  EXPECT_FALSE(inserted_ada);
  EXPECT_TRUE(inserted_grace);
  EXPECT_EQ(ada->second, 12);
  EXPECT_EQ(grace->second, 20);

  // insert_or_assign 对已有 key 赋值，对新 key 插入，并用 bool 区分两条路径。
  // 普通 insert 遇到重复 key 时保留旧 mapped value，不会执行替换。
}

TEST(OrderedAssociative, TransparentComparatorAvoidsConstructingAKeyForLookup) {
  std::map<std::string, int, std::less<>> scores{{"Ada", 10}, {"Grace", 20}};
  const std::string_view query = "Grace";

  auto found = scores.find(query);

  ASSERT_NE(found, scores.end());
  EXPECT_EQ(found->second, 20);
  EXPECT_TRUE(scores.contains(std::string_view{"Ada"}));
  EXPECT_EQ(scores.count(std::string_view{"missing"}), 0U);

  // std::less<> 有 is_transparent，允许用可与 Key 比较的异构类型查找，避免临时构造
  // std::string。C++20 尚无通用异构 erase(key)；可先异构 find，再 erase(iterator)。
}

TEST(NodeHandle, ExtractAllowsKeyMutationAndReportsInsertionConflicts) {
  std::map<int, std::string> source{{1, "one"}, {2, "two"}};
  std::map<int, std::string> target{{3, "existing"}};

  auto node = source.extract(1);
  ASSERT_FALSE(node.empty());
  EXPECT_FALSE(source.contains(1));
  node.key() = 3;
  node.mapped() = "three";

  auto conflict = target.insert(std::move(node));
  EXPECT_FALSE(conflict.inserted);
  EXPECT_EQ(conflict.position->second, "existing");
  ASSERT_FALSE(conflict.node.empty());

  conflict.node.key() = 4;
  auto success = target.insert(std::move(conflict.node));
  EXPECT_TRUE(success.inserted);
  EXPECT_TRUE(success.node.empty());
  EXPECT_EQ(target.at(4), "three");

  // extract 把节点所有权交给 node handle，key() 因脱离树结构而可修改。插入冲突时，
  // insert_return_type 把未消费节点归还；若忽略它，节点析构会删除该元素。
}

TEST(OrderedAssociative, MergeTransfersOnlyKeysAcceptedByTheDestination) {
  std::set<int> target{1, 3};
  std::set<int> source{2, 3, 4};

  target.merge(source);

  EXPECT_EQ(target, (std::set<int>{1, 2, 3, 4}));
  EXPECT_EQ(source, (std::set<int>{3}));

  std::multiset<int> all{1};
  all.merge(source);
  EXPECT_EQ(all, (std::multiset<int>{1, 3}));
  EXPECT_TRUE(source.empty());

  // unique 目标拒绝重复 key，被拒节点仍留在 source；multi 目标可接收全部等价键。
  // merge 通过节点转移避免元素复制，但 allocator 不兼容会违反前置条件。
}

TEST(MultiAssociative, EquivalentKeysOccupyOneContiguousIteratorRange) {
  std::multimap<std::string, int> events{
      {"build", 1},
      {"test", 2},
      {"build", 3},
      {"build", 4},
  };

  auto [first, last] = events.equal_range("build");
  std::vector<int> build_ids;
  for (auto iterator = first; iterator != last; ++iterator) {
    build_ids.push_back(iterator->second);
  }

  EXPECT_EQ(build_ids, (std::vector<int>{1, 3, 4}));
  EXPECT_EQ(events.count("build"), 3U);
  EXPECT_EQ(events.erase("build"), 3U);
  EXPECT_FALSE(events.contains("build"));

  // multimap/multiset 允许 comparator-equivalent key，并保证它们在迭代顺序中连续。
  // 插入没有“重复失败”分支，erase(key) 会删除整个等价范围并返回实际数量。
}

TEST(OrderedAssociative, EraseIfRemovesByInspectingStoredEntries) {
  std::map<std::string, int> scores{{"Ada", 10}, {"Bjarne", 21}, {"Grace", 30}};

  const auto removed = std::erase_if(scores, [](const auto& entry) {
    return entry.second < 20 || entry.first == "Grace";
  });

  EXPECT_EQ(removed, 2U);
  EXPECT_EQ(scores, (std::map<std::string, int>{{"Bjarne", 21}}));

  // C++20 std::erase_if 为关联容器逐节点调用 predicate 并返回删除数量；predicate
  // 看到的是 pair<const Key, T>，不能借机修改 key。它不要求先执行 remove 搬移元素。
}

}  // namespace
