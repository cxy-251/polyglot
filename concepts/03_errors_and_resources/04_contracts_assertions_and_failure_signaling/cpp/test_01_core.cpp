// 契约、断言与失败信号。
// 共同问题：开发期断言与输入校验如何区分；哪些约束能在编译期表达；
// 调用方如何精确检查失败类型和内容。
//
// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/cpp/language/test_029_concepts_requires_and_constraint_ordering.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace {

template <typename T>
concept AddableToItself = requires(T value) {
  { value + value } -> std::same_as<T>;
};

int positive_port(int value) {
  if (value <= 0) {
    throw std::invalid_argument{"port must be positive"};
  }
  return value;
}

TEST(ContractsConcept, StaticAssertAndConceptsRejectInvalidPrograms) {
  static_assert(sizeof(char) == 1);
  static_assert(AddableToItself<int>);
  static_assert(!AddableToItself<std::exception>);

  SUCCEED();
}

TEST(ContractsConcept, RuntimeValidationUsesTypedExceptions) {
  EXPECT_EQ(positive_port(8080), 8080);
  EXPECT_THROW(positive_port(0), std::invalid_argument);

  try {
    static_cast<void>(positive_port(-1));
    FAIL() << "expected invalid_argument";
  } catch (const std::invalid_argument& error) {
    EXPECT_STREQ(error.what(), "port must be positive");
  }
}

TEST(ContractsConcept, StandardAssertIsAConfigurationDependentDebugCheck) {
#ifdef NDEBUG
  constexpr bool assertions_enabled = false;
#else
  constexpr bool assertions_enabled = true;
#endif

  EXPECT_EQ(assertions_enabled, true);

  // assert 失败通常终止进程且 NDEBUG 可移除它；输入错误应使用返回值或异常。
}

TEST(ContractsConcept, FunctionSignatureProvidesCompileTimeCallBoundary) {
  static_assert(std::is_invocable_r_v<int, decltype(positive_port), int>);
  static_assert(!std::is_invocable_v<decltype(positive_port), std::string>);
}

}  // namespace
