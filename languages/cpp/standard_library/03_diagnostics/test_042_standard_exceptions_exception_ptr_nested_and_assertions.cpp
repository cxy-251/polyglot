// polyglot-covers:
// - cpp.stdlib.diagnostics.standard-exception-hierarchy
// - cpp.stdlib.diagnostics.logic-error-and-runtime-error-families
// - cpp.stdlib.diagnostics.exception-ptr-current-and-make-exception-ptr
// - cpp.stdlib.diagnostics.nested-exception-and-throw-with-nested
// - cpp.stdlib.diagnostics.uncaught-exceptions
// - cpp.stdlib.diagnostics.cassert-and-ndebug
// - cpp.stdlib.diagnostics.static-assert

#include <gtest/gtest.h>

#include <cassert>
#include <exception>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

std::exception_ptr capture_failure() {
  try {
    throw std::out_of_range{"index 9 is outside [0, 3)"};
  } catch (...) {
    return std::current_exception();
  }
}

void parse_configuration() {
  try {
    throw std::invalid_argument{"port is not an integer"};
  } catch (...) {
    std::throw_with_nested(std::runtime_error{"configuration parse failed"});
  }
}

void load_application() {
  try {
    parse_configuration();
  } catch (...) {
    std::throw_with_nested(std::runtime_error{"application startup failed"});
  }
}

void collect_nested_messages(
    const std::exception& error,
    std::vector<std::string>& messages) {
  messages.emplace_back(error.what());
  try {
    std::rethrow_if_nested(error);
  } catch (const std::exception& nested) {
    collect_nested_messages(nested, messages);
  }
}

class UnwindingProbe {
 public:
  explicit UnwindingProbe(std::vector<int>& observations)
      : observations_(observations), baseline_(std::uncaught_exceptions()) {}

  ~UnwindingProbe() {
    observations_.push_back(std::uncaught_exceptions() - baseline_);
  }

 private:
  std::vector<int>& observations_;
  int baseline_;
};

TEST(StandardExceptions, LogicAndRuntimeFamiliesExpressDifferentFailureOrigins) {
  const std::invalid_argument invalid{"bad argument"};
  const std::out_of_range outside{"outside range"};
  const std::overflow_error overflow{"overflow"};

  static_assert(std::is_base_of_v<std::logic_error, std::invalid_argument>);
  static_assert(std::is_base_of_v<std::logic_error, std::out_of_range>);
  static_assert(std::is_base_of_v<std::runtime_error, std::overflow_error>);

  EXPECT_STREQ(invalid.what(), "bad argument");
  EXPECT_STREQ(outside.what(), "outside range");
  EXPECT_STREQ(overflow.what(), "overflow");

  // logic_error 家族表示原则上可由调用前置条件或程序逻辑避免的问题；runtime_error 家族
  // 表示运行环境中才显现的问题。层次只提供分类和消息，不会自动携带结构化错误码。
}

TEST(ExceptionPtr, CapturesTheActiveExceptionForLaterRethrow) {
  const std::exception_ptr failure = capture_failure();
  ASSERT_NE(failure, nullptr);

  try {
    std::rethrow_exception(failure);
    FAIL() << "rethrow_exception must throw";
  } catch (const std::out_of_range& error) {
    EXPECT_STREQ(error.what(), "index 9 is outside [0, 3)");
  }

  // exception_ptr 共享被捕获异常对象的所有权，复制它不会切片动态类型。它适合把工作线程
  // 的失败传回协调线程；空 exception_ptr 不能交给 rethrow_exception。
}

TEST(ExceptionPtr, MakeExceptionPtrDoesNotRequireAnActiveHandler) {
  const auto failure = std::make_exception_ptr(std::runtime_error{"prepared failure"});

  EXPECT_THROW(std::rethrow_exception(failure), std::runtime_error);
  EXPECT_EQ(std::current_exception(), nullptr);

  // current_exception 只在正在处理异常时返回非空指针；make_exception_ptr 从给定对象创建
  // 可延迟抛出的异常状态，适合预先构造异步结果或 promise 的失败值。
}

TEST(NestedExceptions, PreservesContextAtEachAbstractionBoundary) {
  std::vector<std::string> messages;

  try {
    load_application();
    FAIL() << "load_application must throw";
  } catch (const std::exception& error) {
    collect_nested_messages(error, messages);
  }

  EXPECT_EQ(
      messages,
      (std::vector<std::string>{
          "application startup failed",
          "configuration parse failed",
          "port is not an integer",
      }));

  // throw_with_nested 把当前异常保存进新异常的 nested_exception 基类，外层增加上下文又不
  // 丢失根因。rethrow_if_nested 对没有嵌套状态的普通异常什么也不做，递归因而自然停止。
}

TEST(UncaughtExceptions, CountsActivePropagatingExceptionsDuringUnwinding) {
  std::vector<int> observations;

  try {
    UnwindingProbe probe{observations};
    throw std::runtime_error{"failure"};
  } catch (const std::runtime_error&) {
  }

  ASSERT_EQ(observations.size(), 1U);
  EXPECT_EQ(observations.front(), 1);

  // 析构时计数高于构造时表示对象正因异常展开。它可辅助 scope guard 选择 commit/rollback，
  // 但嵌套抛异常会使简单布尔判断失真；析构函数本身仍必须避免再抛出异常。
}

TEST(Assertions, RuntimeAssertDependsOnNdebugWhileStaticAssertNeverDoes) {
  int evaluations = 0;
  assert(++evaluations == 1);

#ifdef NDEBUG
  EXPECT_EQ(evaluations, 0);
#else
  EXPECT_EQ(evaluations, 1);
#endif

  static_assert(sizeof(char) == 1, "the standard defines char as one byte");

  // assert 在 NDEBUG 下连表达式求值也会消失，因此不能把修改状态或必要校验副作用放进去。
  // static_assert 始终在编译期检查常量条件，不受构建模式影响，也没有运行期开销。
}

}  // namespace
