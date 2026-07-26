// 异常传播、匹配与重新抛出。
// 共同问题：抛出的值有什么类型约束；处理器如何匹配；重新抛出是否保留原对象；
// 清理和 finally 在传播路径上的顺序是什么。
//
// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp

#include <gtest/gtest.h>

#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace {

class DomainError : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

struct CleanupMarker {
  std::vector<std::string>& events;
  ~CleanupMarker() { events.push_back("cleanup"); }
};

TEST(ExceptionPropagationConcept, HandlerMatchesByStaticExceptionHierarchy) {
  std::string caught;

  try {
    throw DomainError{"failed"};
  } catch (const std::logic_error&) {
    caught = "logic";
  } catch (const std::runtime_error& error) {
    caught = error.what();
  }

  EXPECT_EQ(caught, "failed");
}

TEST(ExceptionPropagationConcept, BareThrowPreservesTheActiveException) {
  try {
    try {
      throw DomainError{"failed"};
    } catch (const DomainError&) {
      throw;
    }
  } catch (const DomainError& error) {
    EXPECT_STREQ(error.what(), "failed");
  }
}

TEST(ExceptionPropagationConcept, StackUnwindingDestroysObjectsBeforeHandler) {
  std::vector<std::string> events;

  try {
    CleanupMarker marker{events};
    events.push_back("body");
    throw DomainError{"failed"};
  } catch (const DomainError&) {
    events.push_back("caught");
  }

  EXPECT_EQ(events, (std::vector<std::string>{"body", "cleanup", "caught"}));
}

TEST(ExceptionPropagationConcept, NoexceptBoundaryIsPartOfTheFunctionType) {
  auto safe = []() noexcept { return 1; };
  auto may_throw = [] { return 1; };

  static_assert(noexcept(safe()));
  static_assert(!noexcept(may_throw()));
  EXPECT_EQ(safe(), 1);

  // 异常逃出 noexcept 会调用 terminate；这里不执行该不可恢复路径。
}

TEST(ExceptionPropagationConcept, CppCanThrowNonExceptionValuesButTypedCatchIsExact) {
  int caught = 0;

  try {
    throw 42;
  } catch (int value) {
    caught = value;
  }

  EXPECT_EQ(caught, 42);
  // 与 Python 不同，C++ 语法允许抛出任意可复制对象；工程代码仍应使用异常类层次。
}

}  // namespace

