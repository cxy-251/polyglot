// polyglot-covers:
// - cpp.stdlib.containers.unordered-hash-and-key-equality-contract
// - cpp.stdlib.containers.unordered-insert-find-contains-and-erase
// - cpp.stdlib.containers.unordered-bucket-interface-and-unspecified-order
// - cpp.stdlib.containers.unordered-load-factor-reserve-and-rehash
// - cpp.stdlib.containers.unordered-rehash-iterator-and-reference-invalidation
// - cpp.stdlib.containers.unordered-insert-without-rehash-stability
// - cpp.stdlib.containers.unordered-map-subscript-try-emplace-and-insert-or-assign
// - cpp.stdlib.containers.unordered-transparent-heterogeneous-lookup
// - cpp.stdlib.containers.unordered-node-extract-and-merge
// - cpp.stdlib.containers.unordered-multi-equivalent-key-range
// - cpp.stdlib.containers.unordered-associative-erase-if

#include <gtest/gtest.h>

#include <cmath>
#include <cstddef>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {

struct LastDigitHash {
  std::size_t operator()(int value) const noexcept {
    return static_cast<std::size_t>(value % 10);
  }
};

struct LastDigitEqual {
  bool operator()(int left, int right) const noexcept {
    return left % 10 == right % 10;
  }
};

struct ConstantHash {
  std::size_t operator()(int) const noexcept {
    return 0;
  }
};

struct TransparentStringHash {
  using is_transparent = void;

  std::size_t operator()(std::string_view value) const noexcept {
    return std::hash<std::string_view>{}(value);
  }

  std::size_t operator()(const std::string& value) const noexcept {
    return (*this)(std::string_view{value});
  }
};

struct TransparentStringEqual {
  using is_transparent = void;

  bool operator()(std::string_view left, std::string_view right) const noexcept {
    return left == right;
  }
};

TEST(UnorderedAssociative, KeyEqualDefinesUniquenessAndHashMustAgreeWithIt) {
  std::unordered_set<int, LastDigitHash, LastDigitEqual> values;

  auto [twelve, inserted_twelve] = values.insert(12);
  auto [twenty_two, inserted_twenty_two] = values.insert(22);
  auto [thirteen, inserted_thirteen] = values.insert(13);

  EXPECT_TRUE(inserted_twelve);
  EXPECT_FALSE(inserted_twenty_two);
  EXPECT_TRUE(inserted_thirteen);
  EXPECT_EQ(twelve, twenty_two);
  EXPECT_EQ(*twelve, 12);
  EXPECT_EQ(*thirteen, 13);

  // 唯一性由 key_equal 定义；若两个 key 等价，hash 必须返回相同值。本例都按个位处理。
  // 反向不要求成立：不同 key 可以 hash 冲突，容器会在桶中继续用 key_equal 区分。
}

TEST(UnorderedSet, InsertFindContainsAndEraseDoNotPromiseIterationOrder) {
  std::unordered_set<std::string> names{"Ada", "Grace"};

  auto [bjarne, inserted] = names.emplace("Bjarne");
  auto [same, duplicate] = names.insert("Bjarne");

  EXPECT_TRUE(inserted);
  EXPECT_FALSE(duplicate);
  EXPECT_EQ(bjarne, same);
  EXPECT_TRUE(names.contains("Ada"));
  EXPECT_EQ(names.find("missing"), names.end());
  EXPECT_EQ(names.erase("Grace"), 1U);

  std::vector<std::string> observed(names.begin(), names.end());
  EXPECT_EQ(observed.size(), 2U);

  // API 与 set 相似，但迭代顺序由桶布局决定，不能断言插入顺序或排序顺序；
  // reserve/rehash 之后顺序还可能改变。需要稳定输出时应显式排序一份副本。
}

TEST(UnorderedAssociative, BucketInterfaceExposesCollisionsForInspection) {
  std::unordered_set<int, ConstantHash> values{1, 2, 3, 4};
  const auto bucket = values.bucket(1);

  EXPECT_EQ(values.bucket_size(bucket), values.size());

  std::size_t local_count = 0;
  for (auto iterator = values.begin(bucket); iterator != values.end(bucket); ++iterator) {
    ++local_count;
    EXPECT_TRUE(values.contains(*iterator));
  }
  EXPECT_EQ(local_count, values.size());

  // local_iterator 只遍历一个桶，可用于诊断散列分布。ConstantHash 故意制造碰撞；
  // 正确性仍在，但查找退化。真实 hash 应尽量均匀，不能依赖具体 bucket_count 或素数策略。
}

TEST(UnorderedAssociative, ReserveAndRehashControlDifferentQuantities) {
  std::unordered_set<int> values{1, 2, 3};
  values.max_load_factor(0.5F);

  values.reserve(20);
  const auto minimum_for_twenty = static_cast<std::size_t>(
      std::ceil(20.0 / values.max_load_factor()));
  EXPECT_GE(values.bucket_count(), minimum_for_twenty);
  EXPECT_LE(values.load_factor(), values.max_load_factor());

  values.rehash(200);
  EXPECT_GE(values.bucket_count(), 200U);
  EXPECT_EQ(values.size(), 3U);

  // reserve(n) 为至少 n 个元素按 max_load_factor 准备桶，参数是“元素数”；
  // rehash(n) 请求至少 n 个桶，参数是“桶数”。实现可选择更大的合适 bucket_count。
}

TEST(UnorderedAssociative, RehashInvalidatesIteratorsButPreservesElementReferences) {
  std::unordered_map<int, std::string> values{{1, "one"}, {2, "two"}};
  std::string* mapped_address = &values.at(1);
  const auto old_bucket_count = values.bucket_count();

  values.rehash(old_bucket_count * 4 + 1);

  EXPECT_GT(values.bucket_count(), old_bucket_count);
  EXPECT_EQ(mapped_address, &values.at(1));
  EXPECT_EQ(*mapped_address, "one");

  // rehash 使全部 iterator（包括 end）失效，却不移动节点中的元素，所以 pointer/reference
  // 仍有效。这里不保存旧 iterator；继续使用它即使看似能工作也违反标准契约。
}

TEST(UnorderedAssociative, InsertionWithoutRehashKeepsExistingIteratorsValid) {
  std::unordered_set<int> values{1, 2};
  values.reserve(20);
  auto one = values.find(1);
  const auto buckets = values.bucket_count();

  values.insert(3);

  EXPECT_EQ(values.bucket_count(), buckets);
  ASSERT_NE(one, values.end());
  EXPECT_EQ(*one, 1);

  values.erase(2);
  EXPECT_EQ(*one, 1);

  // insert/emplace 只有触发 rehash 才让既有 iterator 失效；预留容量可稳定这一批操作。
  // erase 只使被删元素的 handle 失效，其他 iterator/reference 保持有效。
}

TEST(UnorderedMap, SubscriptTryEmplaceAndInsertOrAssignKeepTheirDistinctSemantics) {
  std::unordered_map<std::string, std::unique_ptr<int>> owners;

  EXPECT_EQ(owners["empty"], nullptr);
  auto [seven, inserted] = owners.try_emplace("seven", std::make_unique<int>(7));
  ASSERT_TRUE(inserted);
  EXPECT_EQ(*seven->second, 7);

  auto candidate = std::make_unique<int>(11);
  auto [existing, duplicate] = owners.try_emplace("seven", std::move(candidate));
  EXPECT_FALSE(duplicate);
  EXPECT_EQ(existing, seven);
  EXPECT_NE(candidate, nullptr);

  auto [assigned, was_inserted] = owners.insert_or_assign(
      "seven",
      std::make_unique<int>(70));
  EXPECT_FALSE(was_inserted);
  EXPECT_EQ(*assigned->second, 70);

  // 三组 API 与 ordered map 语义一致：[] 缺失时默认插入；try_emplace 遇重复 key
  // 不消费 mapped 参数；insert_or_assign 会替换已有值。区别只在散列组织与失效规则。
}

TEST(UnorderedAssociative, TransparentHashAndEqualityEnableHeterogeneousLookup) {
  using Scores = std::unordered_map<
      std::string,
      int,
      TransparentStringHash,
      TransparentStringEqual>;
  Scores scores{{"Ada", 10}, {"Grace", 20}};
  const std::string_view query = "Grace";

  auto found = scores.find(query);

  ASSERT_NE(found, scores.end());
  EXPECT_EQ(found->second, 20);
  EXPECT_TRUE(scores.contains(std::string_view{"Ada"}));
  EXPECT_EQ(scores.count(std::string_view{"missing"}), 0U);

  // C++20 异构查找要求 hasher 与 key_equal 都声明 is_transparent，并能处理查询类型。
  // 两者对异构等价值仍必须遵守“equal => same hash”，否则查找会落入错误桶。
}

TEST(UnorderedAssociative, NodeHandlesCanChangeKeysAndMergeLeavesConflictsBehind) {
  std::unordered_map<int, std::string> source{{1, "one"}, {2, "two"}};
  std::unordered_map<int, std::string> target{{2, "existing"}, {3, "three"}};

  auto node = source.extract(1);
  ASSERT_FALSE(node.empty());
  node.key() = 4;
  node.mapped() = "four";
  auto inserted = target.insert(std::move(node));

  EXPECT_TRUE(inserted.inserted);
  EXPECT_EQ(target.at(4), "four");

  target.merge(source);
  EXPECT_TRUE(source.contains(2));
  EXPECT_EQ(source.size(), 1U);
  EXPECT_EQ(target.at(2), "existing");

  // unordered node handle 也允许脱离容器后修改 key；重新插入会按新 hash 放桶。
  // merge 仅转移目标可接受的节点，重复 key 留在 source，且可能触发目标 rehash。
}

TEST(UnorderedMultiAssociative, EqualRangeContainsAllEquivalentKeys) {
  std::unordered_multimap<std::string, int> events{
      {"build", 1},
      {"test", 2},
      {"build", 3},
      {"build", 4},
  };

  auto [first, last] = events.equal_range("build");
  std::unordered_set<int> ids;
  for (auto iterator = first; iterator != last; ++iterator) {
    EXPECT_EQ(iterator->first, "build");
    ids.insert(iterator->second);
  }

  EXPECT_EQ(ids, (std::unordered_set<int>{1, 3, 4}));
  EXPECT_EQ(events.count("build"), 3U);
  EXPECT_EQ(events.erase("build"), 3U);

  // 等价键在迭代顺序中仍形成一个相邻子范围，equal_range 可完整遍历；范围内部
  // 及不同桶的总体次序都不应依赖。multi 容器的 erase(key) 会删除全部等价项。
}

TEST(UnorderedAssociative, EraseIfDoesNotDependOnBucketIterationOrder) {
  std::unordered_map<int, std::string> values{
      {1, "keep"},
      {2, "drop"},
      {3, "keep"},
  };

  const auto removed = std::erase_if(values, [](const auto& entry) {
    return entry.second == "drop";
  });

  EXPECT_EQ(removed, 1U);
  EXPECT_TRUE(values.contains(1));
  EXPECT_FALSE(values.contains(2));
  EXPECT_TRUE(values.contains(3));

  // erase_if 封装安全的遍历与 erase(iterator) 推进方式；predicate 只判断当前 entry，
  // 不应依赖访问顺序，也不应在回调内部触发同一容器 rehash。
}

}  // namespace
