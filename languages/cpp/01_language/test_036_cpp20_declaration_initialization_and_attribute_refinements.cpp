// polyglot-covers:
// - cpp.language.conditional-explicit
// - cpp.language.parenthesized-aggregate-initialization
// - cpp.language.range-for-init-statement
// - cpp.language.standard-attributes
// - cpp.language.nodiscard-reason
// - cpp.language.likely-and-unlikely-attributes
// - cpp.language.attribute-feature-test

#include <gtest/gtest.h>

#include <concepts>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class SwitchValue {
 public:
  template <std::integral Value>
  explicit(std::same_as<std::remove_cvref_t<Value>, bool>)
      SwitchValue(Value value)
      : enabled_(value != 0) {}

  bool enabled() const { return enabled_; }

 private:
  bool enabled_;
};

struct Point {
  int x;
  int y;
};

[[nodiscard("validation result must be checked")]]
bool valid_identifier(const std::string& text) {
  return !text.empty() && text.front() != ' ';
}

[[deprecated("use valid_identifier instead"), maybe_unused]]
bool legacy_valid_identifier(const std::string& text) {
  return !text.empty();
}

int normalized_sign(int value) {
  if (value >= 0) [[likely]] {
    return 1;
  } else [[unlikely]] {
    return -1;
  }
}

TEST(ConditionalExplicit, OneConstructorCanVaryItsImplicitConversionPolicy) {
  static_assert(std::is_convertible_v<int, SwitchValue>);
  static_assert(!std::is_convertible_v<bool, SwitchValue>);
  static_assert(std::is_constructible_v<SwitchValue, bool>);

  SwitchValue from_integer = 2;
  SwitchValue from_boolean{true};
  EXPECT_TRUE(from_integer.enabled());
  EXPECT_TRUE(from_boolean.enabled());

  // explicit(condition) 在实例化后决定构造函数是否允许隐式转换。bool 分支仍可直接构造，
  // 但不能悄悄参与复制初始化；这比复制两套几乎相同的构造函数更容易保持约束一致。
}

TEST(AggregateInitialization, Cpp20AllowsDirectInitializationWithParentheses) {
  Point parenthesized(3, 4);
  Point braced{5, 6};

  EXPECT_EQ(parenthesized.x + parenthesized.y, 7);
  EXPECT_EQ(braced.x + braced.y, 11);

  // C++20 aggregate 支持 `T(args...)`，成员仍按声明顺序初始化。但圆括号形式不支持
  // designated initializer，且不像列表初始化那样拒绝 narrowing，安全边界不能混为一谈。
}

TEST(RangeFor, InitStatementOwnsStateForTheWholeLoop) {
  const std::vector<int> source{1, 2, 3};
  int sum = 0;

  for (auto owned = source; int& value : owned) {
    value *= 2;
    sum += value;
  }

  EXPECT_EQ(sum, 12);
  EXPECT_EQ(source, (std::vector<int>{1, 2, 3}));

  // range-for 的 init-statement 名称活到循环结束，可用于先取得所有权或保存锁，再让
  // range-expression 引用这份状态。它不改变循环变量按值或按引用的原有规则。
}

TEST(Attributes, StandardAttributesCarryDiagnosticsAndOptimizationHints) {
  [[maybe_unused]] constexpr int documentation_only_example = 42;

  EXPECT_TRUE(valid_identifier("worker"));
  EXPECT_FALSE(valid_identifier(" bad"));
  EXPECT_EQ(normalized_sign(7), 1);
  EXPECT_EQ(normalized_sign(-7), -1);

  // nodiscard 的 reason 会进入忽略结果的诊断；deprecated API 在严格 -Werror 构建中不能
  // 故意调用，所以这里只保留声明。likely/unlikely 只提供优化提示，不改变分支语义。
}

TEST(Attributes, FeatureTestReportsWhetherAnAttributeIsRecognized) {
#ifdef __has_cpp_attribute
  static_assert(__has_cpp_attribute(nodiscard) >= 201603L);
  static_assert(__has_cpp_attribute(maybe_unused) >= 201603L);
#endif
  SUCCEED();

  // __has_cpp_attribute 可在预处理阶段做兼容封装，结果表示实现声称支持的标准版本。
  // 未识别属性通常会被忽略并可能告警，因此仍要在目标工具链的严格警告模式下验证。
}

}  // namespace
