// 可调用对象适配与偏应用。
// 共同问题：如何预绑定参数；包装器如何保留调用契约；如何统一不同 callable；
// 适配器是否复制还是引用状态。
//
// polyglot-family: functions_and_calls
// polyglot-concept: callable_adaptation_and_partial_application
// polyglot-related: languages/cpp/language/test_007_lambda_captures_generic_and_constexpr.cpp

#include <gtest/gtest.h>

#include <functional>
#include <string>
#include <type_traits>
#include <utility>

namespace {

int add(int left, int right) {
  return left + right;
}

TEST(CallableAdaptationConcept, BindFrontPrebindsLeadingArgumentsByValue) {
  int offset = 2;
  auto add_offset = std::bind_front(add, offset);
  offset = 10;

  EXPECT_EQ(add_offset(3), 5);
}

TEST(CallableAdaptationConcept, ReferenceWrapperRequestsSharedMutableState) {
  int offset = 2;
  auto read = [](const int& value) { return value; };
  auto read_offset = std::bind_front(read, std::cref(offset));

  offset = 10;

  EXPECT_EQ(read_offset(), 10);
}

TEST(CallableAdaptationConcept, FunctionErasesDifferentCallableTypes) {
  struct Scale {
    int factor;
    int operator()(int value) const { return value * factor; }
  };

  std::function<int(int)> operation = Scale{3};
  EXPECT_EQ(operation(4), 12);

  operation = [](int value) { return -value; };
  EXPECT_EQ(operation(4), -4);
}

TEST(CallableAdaptationConcept, NotFnAndInvokePreserveCallableRules) {
  auto is_even = [](int value) { return value % 2 == 0; };
  auto is_odd = std::not_fn(is_even);

  EXPECT_TRUE(std::invoke(is_odd, 3));
  EXPECT_FALSE(std::invoke(is_odd, 4));
}

TEST(CallableAdaptationConcept, AdaptedSignatureIsCheckedAtCompileTime) {
  auto add_two = std::bind_front(add, 2);

  static_assert(std::is_invocable_r_v<int, decltype(add_two), int>);
  static_assert(!std::is_invocable_v<decltype(add_two)>);

  // C++ 适配器的类型记录调用约束；错误实参数量通常在编译期失败。
}

}  // namespace

