// 运算符与协议定制。
// 共同问题：类型能否重载运算符；左右操作数如何协商；转换协议何时触发；
// 不支持的组合在编译期还是运行期失败。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: operator_and_protocol_customization
// polyglot-related: languages/cpp/language/test_010_operator_overloading_conversions_and_spaceship.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <type_traits>

namespace {

class Distance {
 public:
  explicit Distance(int meters) : meters_(meters) {}

  int meters() const { return meters_; }
  explicit operator bool() const { return meters_ != 0; }

  friend Distance operator+(Distance left, Distance right) {
    return Distance{left.meters_ + right.meters_};
  }

  bool operator==(const Distance&) const = default;

 private:
  int meters_;
};

template <typename Left, typename Right>
concept Addable = requires(Left left, Right right) {
  left + right;
};

TEST(OperatorCustomizationConcept, OverloadedOperatorDefinesDomainValueSemantics) {
  Distance result = Distance{2} + Distance{3};

  EXPECT_EQ(result, Distance{5});
  EXPECT_EQ(result.meters(), 5);
}

TEST(OperatorCustomizationConcept, UnsupportedCombinationFailsAtCompileTime) {
  static_assert(Addable<Distance, Distance>);
  static_assert(!Addable<Distance, int>);
}

TEST(OperatorCustomizationConcept, ExplicitConversionWorksInBooleanContext) {
  Distance zero{0};
  Distance three{3};

  EXPECT_FALSE(zero);
  EXPECT_TRUE(three);
  static_assert(!std::is_convertible_v<Distance, int>);
}

TEST(OperatorCustomizationConcept, BuiltinOperatorRulesCannotBeReplacedGlobally) {
  EXPECT_EQ(2 + 3, 5);

  // 至少一个操作数必须是类或枚举类型；不能像补丁一样重定义两个 int 的 +。
}

}  // namespace

