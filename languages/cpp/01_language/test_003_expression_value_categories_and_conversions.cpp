// polyglot-covers:
// - cpp.language.expression-value-categories
// - cpp.language.temporary-materialization
// - cpp.language.array-and-function-decay
// - cpp.language.integral-promotions-and-usual-arithmetic-conversions
// - cpp.language.contextual-conversion-to-bool
// - cpp.language.move-is-a-cast

#include <gtest/gtest.h>

#include <array>
#include <string>
#include <type_traits>
#include <utility>

namespace {

std::string make_text() { return "temporary"; }
int increment(int value) { return value + 1; }

class ExplicitFlag {
 public:
  explicit ExplicitFlag(bool value) : value_(value) {}
  explicit operator bool() const { return value_; }

 private:
  bool value_;
};

TEST(ValueCategories, DecltypeCanObserveLvalueXvalueAndPrvalue) {
  std::string text{"named object"};

  using NamedExpression = decltype((text));
  using MovedExpression = decltype((std::move(text)));
  using TemporaryExpression = decltype((make_text()));

  static_assert(std::is_same_v<NamedExpression, std::string&>);
  static_assert(std::is_same_v<MovedExpression, std::string&&>);
  static_assert(std::is_same_v<TemporaryExpression, std::string>);

  // 有名字的对象表达式是 lvalue；std::move 只把表达式转换为 xvalue；返回临时值的
  // 函数调用是 prvalue。三者共同决定引用绑定、重载选择以及是否允许移动资源。
  EXPECT_EQ(text, "named object");
}

TEST(ValueCategories, AVariableNamedAsRvalueReferenceIsStillAnLvalue) {
  std::string source{"payload"};
  std::string&& alias = std::move(source);

  static_assert(std::is_same_v<decltype(alias), std::string&&>);
  static_assert(std::is_same_v<decltype((alias)), std::string&>);

  alias += " changed";
  EXPECT_EQ(source, "payload changed");

  // 声明类型中的 && 不会让每次使用变量都自动变成右值。变量一旦有名字，表达式就是
  // lvalue；需要再次允许移动时，必须显式使用 std::move 或正确的完美转发。
}

TEST(ValueCategories, MoveDoesNotMoveUntilAConstructorOrAssignmentConsumesIt) {
  std::string source{"resource"};
  std::string&& cast_result = std::move(source);

  EXPECT_EQ(cast_result, "resource");
  EXPECT_EQ(source, "resource");

  std::string destination{std::move(source)};
  EXPECT_EQ(destination, "resource");

  // 移动构造后，source 仍然有效但内容未指定；不能把“当前实现通常变空”写成断言。
  source = "reused";
  EXPECT_EQ(source, "reused");
}

TEST(TypeDeduction, AutoDropsReferencesWhileDecltypeAutoCanPreserveThem) {
  int number = 7;

  auto copied = (number);
  decltype(auto) preserved = (number);

  static_assert(std::is_same_v<decltype(copied), int>);
  static_assert(std::is_same_v<decltype(preserved), int&>);

  copied = 9;
  EXPECT_EQ(number, 7);

  preserved = 11;
  EXPECT_EQ(number, 11);

  // decltype(auto) 使用 decltype 的规则；多出的括号让表达式按 lvalue 得到 int&。
  // 普通 auto 则像模板按值参数一样丢弃顶层 cv 和引用，产生独立副本。
}

TEST(StandardConversions, ArraysAndFunctionsUsuallyDecayToPointers) {
  int values[3]{2, 3, 5};
  auto array_pointer = values;
  auto& array_reference = values;

  static_assert(std::is_same_v<decltype(array_pointer), int*>);
  static_assert(std::is_same_v<decltype(array_reference), int (&)[3]>);
  EXPECT_EQ(array_pointer[2], 5);
  EXPECT_EQ(std::size(array_reference), 3U);

  auto function_pointer = increment;
  static_assert(std::is_same_v<decltype(function_pointer), int (*)(int)>);
  EXPECT_EQ(function_pointer(8), 9);

  // auto 按值推导触发 array-to-pointer 和 function-to-pointer 转换；用引用接住数组
  // 才保留长度。sizeof、取地址和引用绑定等语境不会进行通常的数组退化。
}

TEST(StandardConversions, PromotionsAffectTheTypeBeforeArithmeticRuns) {
  short left = 10;
  short right = 20;
  auto sum = left + right;

  static_assert(std::is_same_v<decltype(sum), int>);
  static_assert(std::is_same_v<decltype(1 + 2.0), double>);
  EXPECT_EQ(sum, 30);

  EXPECT_EQ(5 / 2, 2);
  EXPECT_DOUBLE_EQ(5 / 2.0, 2.5);

  // 小整数类型通常先进行 integral promotion，再参与算术。表达式结果类型不是简单
  // 地沿用操作数声明类型；整数除法也在转换完成后才执行，不会自动保留小数。
}

TEST(StandardConversions, SignedAndUnsignedMixingNeedsAnIntentionalComparison) {
  int signed_value = -1;
  unsigned int unsigned_value = 1;

  unsigned int converted = static_cast<unsigned int>(signed_value);
  EXPECT_GT(converted, unsigned_value);
  EXPECT_TRUE(std::cmp_less(signed_value, unsigned_value));

  // 直接写 signed_value < unsigned_value 时，通常会先把 -1 转成很大的 unsigned，
  // 得到违背直觉的 false。C++20 的 cmp_less 按数学意义比较不同符号的整数。
}

TEST(ContextualConversion, ExplicitBoolWorksInConditionsButNotImplicitAssignment) {
  ExplicitFlag enabled{true};
  ExplicitFlag disabled{false};

  static_assert(!std::is_convertible_v<ExplicitFlag, bool>);
  EXPECT_TRUE(static_cast<bool>(enabled));
  EXPECT_FALSE(static_cast<bool>(disabled));

  int branch = 0;
  if (enabled) {
    branch = 1;
  }
  EXPECT_EQ(branch, 1);

  // if、while、逻辑运算符和 ?: 的条件允许 contextual conversion to bool，因此会
  // 考虑 explicit operator bool；普通的 bool value = enabled 则不会接受显式转换。
}

}  // namespace
