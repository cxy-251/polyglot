// 断言配置与运行时契约边界。
// 共同问题：开发断言能否被配置移除；类型约束是否检查运行时值；
// 公共 API 应采用什么稳定失败通道。
//
// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/cpp/language/test_029_concepts_requires_and_constraint_ordering.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <stdexcept>
#include <type_traits>

namespace {

template <std::integral T>
int positive(T value) {
  if (value <= 0) {
    throw std::domain_error{"must be positive"};
  }
  return static_cast<int>(value);
}

template <typename T>
concept AcceptsPositive = requires(T value) {
  { positive(value) } -> std::same_as<int>;
};

TEST(ContractBoundaryConcept, ConstraintChecksTypeButFunctionChecksValue) {
  static_assert(AcceptsPositive<int>);
  static_assert(!AcceptsPositive<double>);

  EXPECT_EQ(positive(2), 2);
  EXPECT_THROW(positive(-2), std::domain_error);

  // requires 只证明调用表达式对 int 合法，不能证明某个运行时 int 为正；值契约仍需
  // 显式分支、返回类型或异常。编译期非法 double 调用不通过制造编译失败来演示。
}

TEST(ContractBoundaryConcept, AssertAvailabilityComesFromBuildConfiguration) {
#ifdef NDEBUG
  constexpr bool standard_assertions_enabled = false;
#else
  constexpr bool standard_assertions_enabled = true;
#endif

  static_assert(std::is_same_v<decltype(standard_assertions_enabled), const bool>);
  EXPECT_TRUE(standard_assertions_enabled);

  // 本仓库测试构建未定义 NDEBUG；其他构建可删除 assert 表达式，不能据此实现公共校验。
}

}  // namespace
