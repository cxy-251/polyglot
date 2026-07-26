// 横向概念 003｜参数绑定、对象传递与默认值。
// 共同问题：缺少或多余实参如何处理；修改与重新绑定是否影响调用者；
// 默认表达式何时求值；如何表达命名选项和可变参数。
//
// polyglot-family: functions_and_calls
// polyglot-concept: argument_passing
// polyglot-related: languages/cpp/language/test_006_functions_parameters_defaults_and_overload_resolution.cpp

#include <gtest/gtest.h>

#include <functional>
#include <string>
#include <type_traits>
#include <vector>

namespace {

int default_calls = 0;

int next_default() {
  default_calls += 1;
  return default_calls;
}

int use_default(int value = next_default()) {
  return value;
}

std::vector<std::string> append_by_value(std::vector<std::string> values) {
  values.push_back("copy");
  return values;
}

void append_by_reference(std::vector<std::string>& values) {
  values.push_back("reference");
}

TEST(ArgumentPassingConcept, ArityAndTypesAreCheckedBeforeExecution) {
  auto pair = [](int first, int second) { return first + second; };

  static_assert(std::is_invocable_v<decltype(pair), int, int>);
  static_assert(!std::is_invocable_v<decltype(pair), int>);
  static_assert(!std::is_invocable_v<decltype(pair), int, int, int>);
  EXPECT_EQ(pair(2, 3), 5);
}

TEST(ArgumentPassingConcept, ValueCopiesAndReferencesExposeDifferentMutation) {
  std::vector<std::string> original{"before"};

  auto copied = append_by_value(original);
  EXPECT_EQ(original, (std::vector<std::string>{"before"}));
  EXPECT_EQ(copied, (std::vector<std::string>{"before", "copy"}));

  append_by_reference(original);
  EXPECT_EQ(original, (std::vector<std::string>{"before", "reference"}));
}

TEST(ArgumentPassingConcept, DefaultExpressionRunsAtEachOmittedCall) {
  default_calls = 0;

  EXPECT_EQ(use_default(), 1);
  EXPECT_EQ(use_default(), 2);
  EXPECT_EQ(use_default(20), 20);
  EXPECT_EQ(default_calls, 2);
}

TEST(ArgumentPassingConcept, OptionsObjectAndParameterPackExpressFlexibleCalls) {
  struct Options {
    bool urgent = false;
  };
  auto describe = [](std::string task, Options options) {
    return task + (options.urgent ? ":urgent" : ":normal");
  };
  auto sum = []<typename... Values>(Values... values) {
    return (0 + ... + values);
  };

  EXPECT_EQ(describe("build", Options{.urgent = true}), "build:urgent");
  EXPECT_EQ(sum(1, 2, 3), 6);

  // C++ 没有 Python 关键字实参；配置结构体只是在调用方显式模拟具名选项。
}

}  // namespace
