// 横向概念 001｜真假值与逻辑运算结果。
// 共同问题：数值零、空文本、空集合和空指针如何判断；自定义对象能否定义真假；
// 逻辑运算符返回布尔值还是原操作数。
//
// polyglot-concept: truthiness
// polyglot-related: languages/cpp/language/test_010_operator_overloading_conversions_and_spaceship.cpp

#include <gtest/gtest.h>

#include <string>
#include <type_traits>
#include <vector>

namespace {

template <typename T>
concept ContextuallyBoolean = requires(T value) {
  value ? 1 : 0;
};

class ExplicitFlag {
 public:
  explicit ExplicitFlag(bool enabled) : enabled_(enabled) {}
  explicit operator bool() const { return enabled_; }

 private:
  bool enabled_;
};

TEST(TruthinessConcept, ZeroAndNullPointerAreFalse) {
  int* pointer = nullptr;

  EXPECT_FALSE(0);
  EXPECT_TRUE(1);
  EXPECT_FALSE(pointer);
  static_assert(ContextuallyBoolean<int>);
  static_assert(ContextuallyBoolean<int*>);
}

TEST(TruthinessConcept, EmptyTextAndCollectionsRequireExplicitQueries) {
  std::string text;
  std::vector<int> values;

  static_assert(!ContextuallyBoolean<std::string>);
  static_assert(!ContextuallyBoolean<std::vector<int>>);
  EXPECT_TRUE(text.empty());
  EXPECT_TRUE(values.empty());

  // C++ 没有 Python 式“空容器为假”协议，也没有 JavaScript 式“所有对象为真”规则。
  // 容器必须调用 empty() 或比较 size()，这样条件不会隐藏线性或领域相关的含义。
}

TEST(TruthinessConcept, CustomTypeCanOptIntoContextualBooleanConversion) {
  ExplicitFlag disabled{false};
  ExplicitFlag enabled{true};

  EXPECT_FALSE(disabled);
  EXPECT_TRUE(enabled);
  static_assert(!std::is_convertible_v<ExplicitFlag, int>);
}

TEST(TruthinessConcept, BuiltinLogicalOperatorsAlwaysReturnBool) {
  static_assert(std::is_same_v<decltype(1 && 2), bool>);
  static_assert(std::is_same_v<decltype(0 || 2), bool>);

  EXPECT_TRUE(1 && 2);
  EXPECT_TRUE(0 || 2);

  // 这不同于 Python 和 JavaScript：内置 && / || 不返回被选中的原操作数。
}

}  // namespace
