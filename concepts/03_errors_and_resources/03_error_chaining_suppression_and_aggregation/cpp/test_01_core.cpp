// 错误链、抑制与聚合。
// 共同问题：包装错误如何保留原因；隐式上下文能否隐藏；多个失败如何携带；
// 清理失败与主体失败如何同时保留。
//
// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp

#include <gtest/gtest.h>

#include <exception>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace {

void wrap_failure() {
  try {
    throw std::invalid_argument{"invalid input"};
  } catch (...) {
    std::throw_with_nested(std::runtime_error{"load failed"});
  }
}

TEST(ErrorChainingConcept, NestedExceptionExplicitlyPreservesOneCause) {
  try {
    wrap_failure();
    FAIL() << "expected exception";
  } catch (const std::runtime_error& outer) {
    EXPECT_STREQ(outer.what(), "load failed");
    try {
      std::rethrow_if_nested(outer);
      FAIL() << "expected nested exception";
    } catch (const std::invalid_argument& cause) {
      EXPECT_STREQ(cause.what(), "invalid input");
    }
  }
}

TEST(ErrorChainingConcept, ExceptionPtrStoresAPropagatingFailureValue) {
  std::exception_ptr stored;
  try {
    throw std::runtime_error{"failed"};
  } catch (...) {
    stored = std::current_exception();
  }

  ASSERT_NE(stored, nullptr);
  EXPECT_THROW(std::rethrow_exception(stored), std::runtime_error);
}

TEST(ErrorChainingConcept, MultipleFailuresNeedAnExplicitContainer) {
  std::vector<std::exception_ptr> failures;
  for (const char* message : {"first", "second"}) {
    try {
      throw std::runtime_error{message};
    } catch (...) {
      failures.push_back(std::current_exception());
    }
  }

  EXPECT_EQ(failures.size(), 2U);

  // C++20 没有 AggregateError/ExceptionGroup；容器的传播、格式化与处理策略由应用定义。
}

TEST(ErrorChainingConcept, DestructorsCannotSuppressOrReturnAnErrorChain) {
  struct SafeCleanup {
    ~SafeCleanup() noexcept = default;
  };

  static_assert(std::is_nothrow_destructible_v<SafeCleanup>);

  // 栈展开期间析构再抛异常会 terminate；RAII 清理应 noexcept，并用其他通道记录清理失败。
}

}  // namespace
