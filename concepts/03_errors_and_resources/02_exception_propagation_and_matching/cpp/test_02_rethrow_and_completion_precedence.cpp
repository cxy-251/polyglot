// 重新抛出、诊断信息与完成方式竞争。
// 共同问题：重新抛出是否保留原对象和诊断起点；清理块产生 return 或 throw 时，
// 原有完成方式是否继续传播。
//
// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp

#include <gtest/gtest.h>

#include <exception>
#include <stdexcept>
#include <string>

namespace {

class DomainError : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

TEST(RethrowConcept, BareThrowKeepsTheActiveExceptionObject) {
  const DomainError* inner_address = nullptr;
  const DomainError* outer_address = nullptr;

  try {
    try {
      throw DomainError{"failed"};
    } catch (const DomainError& error) {
      inner_address = &error;
      throw;
    }
  } catch (const DomainError& error) {
    outer_address = &error;
    EXPECT_STREQ(error.what(), "failed");
  }

  EXPECT_EQ(inner_address, outer_address);

  // throw; 重新激活当前异常对象。C++ 不标准化堆栈字符串；诊断堆栈需实现或库支持。
}

TEST(RethrowConcept, ExceptionPtrPreservesDynamicTypeAcrossALaterBoundary) {
  std::exception_ptr stored;

  try {
    throw DomainError{"failed"};
  } catch (...) {
    stored = std::current_exception();
  }

  try {
    std::rethrow_exception(stored);
  } catch (const DomainError& error) {
    EXPECT_STREQ(error.what(), "failed");
  }
}

TEST(RethrowConcept, CopyingIntoABaseValueSlicesTheDynamicExceptionType) {
  std::string observed;

  try {
    throw DomainError{"failed"};
  } catch (const DomainError& error) {
    std::runtime_error sliced = error;
    observed = typeid(sliced).name();
    EXPECT_STREQ(sliced.what(), "failed");
  }

  EXPECT_EQ(observed, typeid(std::runtime_error).name());

  // C++ 没有 finally 的 return/throw completion-record 竞争；RAII 析构不能返回值，
  // 且栈展开期间析构异常逃出会 terminate，所以不能安全仿造 Python/JavaScript 覆盖语义。
}

}  // namespace
