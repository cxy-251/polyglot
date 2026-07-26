// 排序、哈希与键语义。
// 共同问题：排序依赖什么关系；相等对象是否必须同哈希；哪些值能作为键；
// 映射与集合如何判断同一个键。
//
// polyglot-family: values_and_comparison
// polyglot-concept: ordering_hashing_and_key_semantics
// polyglot-related: languages/cpp/language/test_010_operator_overloading_conversions_and_spaceship.cpp

#include <gtest/gtest.h>

#include <algorithm>
#include <compare>
#include <functional>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

struct Ticket {
  int number;

  auto operator<=>(const Ticket&) const = default;
};

struct TicketHash {
  std::size_t operator()(const Ticket& ticket) const noexcept {
    return std::hash<int>{}(ticket.number);
  }
};

TEST(KeySemanticsConcept, OneValueRelationCanDriveEqualityAndOrdering) {
  Ticket first{2};
  Ticket same{2};
  Ticket earlier{1};

  EXPECT_EQ(first, same);
  EXPECT_LT(earlier, first);

  std::vector<Ticket> values{first, earlier};
  std::sort(values.begin(), values.end());
  EXPECT_EQ(values, (std::vector<Ticket>{{1}, {2}}));
}

TEST(KeySemanticsConcept, OrderedAndUnorderedMapsUseDifferentCustomization) {
  std::map<Ticket, std::string> ordered;
  std::unordered_map<Ticket, std::string, TicketHash> hashed;

  ordered[{2}] = "value";
  hashed[{2}] = "value";

  EXPECT_EQ(ordered.at(Ticket{2}), "value");
  EXPECT_EQ(hashed.at(Ticket{2}), "value");
  EXPECT_EQ(TicketHash{}(Ticket{2}), TicketHash{}(Ticket{2}));
}

TEST(KeySemanticsConcept, EqualKeysMustShareAHashButCollisionsRemainAllowed) {
  Ticket first{2};
  Ticket same{2};
  Ticket different{3};

  EXPECT_EQ(first, same);
  EXPECT_EQ(TicketHash{}(first), TicketHash{}(same));
  EXPECT_NE(first, different);

  // “相等则同哈希”是 unordered 容器契约；反向不成立，哈希碰撞必须再用相等判断。
}

TEST(KeySemanticsConcept, ComparatorMustProvideStrictWeakOrdering) {
  auto descending = [](const Ticket& left, const Ticket& right) {
    return left.number > right.number;
  };
  std::vector<Ticket> values{{1}, {3}, {2}};

  std::sort(values.begin(), values.end(), descending);

  EXPECT_EQ(values, (std::vector<Ticket>{{3}, {2}, {1}}));
  // 违反严格弱序会破坏算法前提；这里不通过不一致比较器制造未指定结果。
}

}  // namespace
