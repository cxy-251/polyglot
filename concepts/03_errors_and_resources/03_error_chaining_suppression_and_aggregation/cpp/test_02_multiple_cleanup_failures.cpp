// 多个清理失败的保留方式。
// 共同问题：主体失败后多个清理也失败时，哪个错误成为最外层；其余失败如何保留；
// 没有内置聚合协议时如何显式保存全部结果。
//
// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp

#include <gtest/gtest.h>

#include <exception>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::vector<std::exception_ptr> close_all(
    const std::vector<std::function<void()>>& cleanups) {
  std::vector<std::exception_ptr> failures;
  for (auto cleanup = cleanups.rbegin(); cleanup != cleanups.rend(); ++cleanup) {
    try {
      (*cleanup)();
    } catch (...) {
      failures.push_back(std::current_exception());
    }
  }
  return failures;
}

std::string message_from(const std::exception_ptr& failure) {
  try {
    std::rethrow_exception(failure);
  } catch (const std::exception& error) {
    return error.what();
  } catch (...) {
    return "<non-standard exception>";
  }
}

TEST(MultipleFailureConcept, ExplicitCleanupRunnerCollectsEveryFailureInLifoOrder) {
  std::vector<std::string> events;
  const std::vector<std::function<void()>> cleanups{
      [&] {
        events.push_back("cleanup:first");
        throw std::runtime_error{"first"};
      },
      [&] {
        events.push_back("cleanup:second");
        throw std::logic_error{"second"};
      },
  };

  const std::vector<std::exception_ptr> failures = close_all(cleanups);

  EXPECT_EQ(
      events,
      (std::vector<std::string>{"cleanup:second", "cleanup:first"}));
  ASSERT_EQ(failures.size(), 2U);
  EXPECT_EQ(message_from(failures[0]), "second");
  EXPECT_EQ(message_from(failures[1]), "first");

  // C++20 没有自动 SuppressedError/ExceptionGroup。noexcept 析构负责安全收尾；需要报告
  // 多个清理错误时，应在非析构控制器中显式捕获 exception_ptr，避免双异常 terminate。
}

}  // namespace
