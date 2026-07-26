// 空值、缺失状态与可选值。
// 共同问题：语言有几种空状态；缺失成员如何区分；默认值是否会吞掉有效假值；
// 读取空状态时在何处失败。
//
// polyglot-family: values_and_comparison
// polyglot-concept: null_missing_and_optional_values
// polyglot-related: languages/cpp/language/test_003_expression_value_categories_and_conversions.cpp

#include <gtest/gtest.h>

#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace {

TEST(OptionalValuesConcept, NullPointerAndDisengagedOptionalAreDifferentTypes) {
  int* pointer = nullptr;
  std::optional<int> value = std::nullopt;

  EXPECT_EQ(pointer, nullptr);
  EXPECT_FALSE(value.has_value());
  static_assert(!std::is_same_v<decltype(pointer), decltype(value)>);
}

TEST(OptionalValuesConcept, EngagementIsIndependentOfContainedTruthValue) {
  std::optional<bool> disabled = false;
  std::optional<int> zero = 0;

  EXPECT_TRUE(disabled.has_value());
  EXPECT_FALSE(*disabled);
  EXPECT_TRUE(zero.has_value());
  EXPECT_EQ(*zero, 0);

  // `if (disabled)` 检查是否有值，不检查所含 bool；这不同于 Python/JavaScript 的空值判断。
}

TEST(OptionalValuesConcept, EmptyAccessFailsAtTheExplicitValueBoundary) {
  std::optional<std::string> missing;

  EXPECT_THROW(static_cast<void>(missing.value()), std::bad_optional_access);
  EXPECT_EQ(missing.value_or("fallback"), "fallback");

  missing = "";
  EXPECT_TRUE(missing.has_value());
  EXPECT_EQ(missing.value_or("fallback"), "");
}

TEST(OptionalValuesConcept, PointerDereferenceRequiresASeparateSafetyCheck) {
  int answer = 42;
  int* pointer = &answer;

  ASSERT_NE(pointer, nullptr);
  EXPECT_EQ(*pointer, 42);

  // 解引用 nullptr 是未定义行为；optional::value() 则提供可捕获异常，两者不是同一种空状态。
}

}  // namespace
