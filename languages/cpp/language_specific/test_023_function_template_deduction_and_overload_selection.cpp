// polyglot-covers:
// - cpp.language.function-template-argument-deduction
// - cpp.language.deduction-adjustments-for-value-and-reference-parameters
// - cpp.language.array-reference-deduction
// - cpp.language.non-deduced-contexts
// - cpp.language.explicit-template-arguments
// - cpp.language.function-template-and-nontemplate-overload-selection

#include <gtest/gtest.h>

#include <cstddef>
#include <string>
#include <type_traits>

namespace {

template <typename Value>
constexpr bool value_parameter_is_const(Value) {
  return std::is_const_v<Value>;
}

template <typename Value>
constexpr bool reference_parameter_is_const(Value&) {
  return std::is_const_v<Value>;
}

template <typename Value, std::size_t Size>
constexpr std::size_t array_size(Value (&)[Size]) {
  return Size;
}

template <typename Value>
Value choose(Value primary, std::type_identity_t<Value> fallback, bool use_fallback) {
  return use_fallback ? fallback : primary;
}

template <typename Value>
Value make_default() {
  return Value{};
}

std::string describe(int) { return "non-template int"; }

template <typename Value>
std::string describe(Value) {
  return "template exact match";
}

template <typename Value>
Value twice(Value value) {
  return value + value;
}

TEST(TemplateDeduction, ValueParameterDropsTopLevelConstButReferencePreservesIt) {
  const int value = 7;

  EXPECT_FALSE(value_parameter_is_const(value));
  EXPECT_TRUE(reference_parameter_is_const(value));

  // 按值推导先进行数组/函数退化并忽略顶层 cv；Value& 直接从所绑定对象推导，
  // 因而 Value 会保留 const。接口参数形状决定模板看到的是副本类型还是对象类型。
}

TEST(TemplateDeduction, ArrayReferencePreservesTheCompileTimeExtent) {
  int values[5]{};
  const char text[] = "hello";

  static_assert(array_size(values) == 5);
  static_assert(array_size(text) == 6);
  EXPECT_EQ(array_size(values), 5U);

  // Value (&)[Size] 阻止 array-to-pointer decay，并从数组类型推导 Size。字符串数组的
  // extent 包含结尾零字符；若参数写成 Value*，长度信息在进入函数前已经丢失。
}

TEST(TemplateDeduction, TypeIdentityCreatesANonDeducedContext) {
  EXPECT_EQ(choose(3, 4, false), 3);
  EXPECT_EQ(choose(3, 4.8, true), 4);

  // 第一个参数推导 Value=int；type_identity_t<Value> 中的 Value 不参与第二次推导，
  // 所以 4.8 在选定 specialization 后转换为 int。若两处都参与推导会产生冲突。
}

TEST(TemplateDeduction, ReturnTypeAloneCannotDetermineTemplateArguments) {
  int integer = make_default<int>();
  std::string text = make_default<std::string>();

  EXPECT_EQ(integer, 0);
  EXPECT_TRUE(text.empty());

  // 赋值目标和普通返回语境不参与函数模板实参推导，因此 make_default() 无法从左侧
  // int 猜出 Value。需要显式模板实参，或把类型信息放进函数参数。
}

TEST(OverloadSelection, NonTemplateWinsOnlyWhenConversionQualityTies) {
  int integer = 1;
  short small = 2;

  EXPECT_EQ(describe(integer), "non-template int");
  EXPECT_EQ(describe(small), "template exact match");

  // 对 int 两个候选都是精确匹配，非模板函数胜出；对 short，模板推导 Value=short 是
  // 精确匹配，优于非模板 short-to-int promotion。非模板并非无条件优先。
}

TEST(TemplateInstantiation, OnlyUsedSpecializationsNeedAValidInstantiatedBody) {
  EXPECT_EQ(twice(4), 8);
  EXPECT_EQ(twice(std::string{"ab"}), "abab");

  // 模板定义会先做不依赖参数的语法检查；依赖 Value 的 `value + value` 在 specialization
  // 被需要时才实例化。为不支持 + 的类型调用 twice 才会触发诊断。
}

}  // namespace
