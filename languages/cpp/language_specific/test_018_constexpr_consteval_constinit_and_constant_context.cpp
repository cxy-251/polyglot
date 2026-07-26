// polyglot-covers:
// - cpp.language.constant-expressions
// - cpp.language.const-versus-constexpr
// - cpp.language.constexpr-functions-runtime-and-compile-time
// - cpp.language.consteval-immediate-functions
// - cpp.language.constinit-static-initialization
// - cpp.language.is-constant-evaluated
// - cpp.language.if-constexpr-discarded-branch

#include <gtest/gtest.h>

#include <string>
#include <type_traits>

namespace {

constinit int mutable_static_value = 41;

constexpr int square(int value) { return value * value; }

consteval int checked_positive_square(int value) {
  if (value < 0) {
    throw "negative immediate argument";
  }
  return value * value;
}

constexpr int evaluation_mode() {
  if (std::is_constant_evaluated()) {
    return 1;
  }
  return 2;
}

template <typename Value>
constexpr auto increment_or_size(const Value& value) {
  if constexpr (std::is_integral_v<Value>) {
    return value + 1;
  } else {
    return value.size();
  }
}

TEST(ConstantExpressions, ConstDoesNotAlwaysMeanCompileTimeConstant) {
  int runtime_input = 7;
  const int runtime_const = runtime_input;
  constexpr int compile_time_constant = 7;

  EXPECT_EQ(runtime_const, compile_time_constant);
  static_assert(compile_time_constant == 7);

  // const 只禁止通过该对象修改值，初始化仍可来自运行期。constexpr 变量必须由常量
  // 表达式初始化并隐含 const，才能用于数组界限、模板实参和 static_assert 等语境。
}

TEST(ConstantExpressions, ConstexprFunctionMayAlsoRunAtRuntime) {
  constexpr int compiled = square(6);
  static_assert(compiled == 36);

  int runtime_input = 8;
  int runtime_result = square(runtime_input);
  EXPECT_EQ(runtime_result, 64);

  // constexpr 让函数“可以”在满足条件时常量求值，并不强迫每次调用都发生在编译期。
  // 同一实现避免维护一套运行期算法和一套元编程算法。
}

TEST(ConstantExpressions, ConstevalFunctionMustProduceAnImmediateConstant) {
  constexpr int result = checked_positive_square(9);
  static_assert(result == 81);
  EXPECT_EQ(result, 81);

  // consteval immediate function 的每个潜在求值调用都必须形成常量表达式。运行期变量
  // 不能直接传入；参数校验失败也会让编译失败，而不是在运行期抛出字符串。
}

TEST(ConstantExpressions, ConstinitPreventsDynamicInitializationButNotMutation) {
  EXPECT_EQ(mutable_static_value, 41);

  mutable_static_value = 42;
  EXPECT_EQ(mutable_static_value, 42);
  mutable_static_value = 41;

  // constinit 只要求 static 或 thread 存储期对象完成静态初始化，避免跨翻译单元动态
  // 初始化顺序问题。它不隐含 const；要禁止后续修改仍需另加 const。
}

TEST(ConstantExpressions, CodeCanObserveItsEvaluationContext) {
  constexpr int compile_time = evaluation_mode();
  int runtime = evaluation_mode();

  static_assert(compile_time == 1);
  EXPECT_EQ(runtime, 2);

  // is_constant_evaluated 适合在保持相同结果语义的前提下选择不同实现路径。不能用它
  // 让编译期和运行期返回互相矛盾的业务答案，否则调用语境会悄悄改变程序含义。
}

TEST(ConstantExpressions, IfConstexprDoesNotInstantiateTheDiscardedBranch) {
  static_assert(increment_or_size(7) == 8);

  std::string text{"hello"};
  EXPECT_EQ(increment_or_size(text), 5U);

  // 对 int 只形成 value + 1，对 string 只形成 value.size()。被丢弃分支仍须在模板外
  // 语法正确，但其中依赖模板参数的无效操作不会为当前 specialization 实例化。
}

}  // namespace
