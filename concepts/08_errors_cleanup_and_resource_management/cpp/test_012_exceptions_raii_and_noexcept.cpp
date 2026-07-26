// polyglot-covers:
// - cpp.language.throw-try-and-handler-matching
// - cpp.language.stack-unwinding-and-raii
// - cpp.language.rethrow-preserves-dynamic-type
// - cpp.language.constructor-failure-cleanup
// - cpp.language.noexcept-operator-and-function-type
// - cpp.language.exception-safety-commit-rollback

#include <gtest/gtest.h>

#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class DomainFailure : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

class UnwindProbe {
 public:
  UnwindProbe(std::vector<std::string>& events, std::string name)
      : events_(events), name_(std::move(name)) {
    events_.push_back("acquire " + name_);
  }

  ~UnwindProbe() { events_.push_back("release " + name_); }

 private:
  std::vector<std::string>& events_;
  std::string name_;
};

void throw_with_resources(std::vector<std::string>& events) {
  UnwindProbe outer{events, "outer"};
  UnwindProbe inner{events, "inner"};
  throw DomainFailure{"failed"};
}

void add_context_and_rethrow() {
  try {
    throw DomainFailure{"original dynamic type"};
  } catch (const std::exception&) {
    throw;
  }
}

class MemberThatMayThrow {
 public:
  MemberThatMayThrow(std::vector<std::string>& events, std::string name, bool fail)
      : events_(events), name_(std::move(name)) {
    events_.push_back("construct " + name_);
    if (fail) {
      throw DomainFailure{"member failure"};
    }
  }

  ~MemberThatMayThrow() { events_.push_back("destroy " + name_); }

 private:
  std::vector<std::string>& events_;
  std::string name_;
};

class PartiallyConstructedOwner {
 public:
  explicit PartiallyConstructedOwner(std::vector<std::string>& events)
      : first_(events, "first", false), second_(events, "second", true) {}

 private:
  MemberThatMayThrow first_;
  MemberThatMayThrow second_;
};

void guaranteed_no_throw() noexcept {}
void potentially_throwing() {}

class TransactionalValue {
 public:
  explicit TransactionalValue(std::vector<int> values) : values_(std::move(values)) {}

  void append_two_or_rollback(int first, int second, bool fail_after_first) {
    std::vector<int> candidate = values_;
    candidate.push_back(first);
    if (fail_after_first) {
      throw DomainFailure{"rollback"};
    }
    candidate.push_back(second);
    values_.swap(candidate);
  }

  [[nodiscard]] const std::vector<int>& values() const { return values_; }

 private:
  std::vector<int> values_;
};

TEST(Exceptions, HandlersMatchFromMostSpecificToMoreGeneral) {
  std::string selected;

  try {
    throw DomainFailure{"problem"};
  } catch (const DomainFailure& error) {
    selected = std::string{"domain: "} + error.what();
  } catch (const std::exception&) {
    selected = "generic";
  }

  EXPECT_EQ(selected, "domain: problem");

  // handler 按源码顺序尝试，派生异常应放在基类异常之前。按 const 引用捕获保留动态
  // 类型并避免复制切片；catch(...) 只能作为最后的兜底。
}

TEST(Exceptions, StackUnwindingDestroysCompletedAutomaticObjects) {
  std::vector<std::string> events;

  EXPECT_THROW(throw_with_resources(events), DomainFailure);
  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "acquire outer",
          "acquire inner",
          "release inner",
          "release outer",
      }));

  // 找到 handler 前，栈展开按逆构造顺序析构已完成的自动对象。资源放入 RAII 类型后，
  // 异常路径和普通 return 使用同一清理机制，不需要手写成对 catch 清理代码。
}

TEST(Exceptions, BareRethrowPreservesTheOriginalExceptionObject) {
  try {
    add_context_and_rethrow();
    FAIL() << "expected an exception";
  } catch (const DomainFailure& error) {
    EXPECT_EQ(std::string{error.what()}, "original dynamic type");
  }

  // handler 内的 `throw;` 重新抛出当前异常对象并保留动态类型。写成 `throw error;`
  // 会创建新对象，还可能按照 handler 参数的静态类型发生切片。
}

TEST(Exceptions, FailedConstructionDestroysOnlyCompletedSubobjects) {
  std::vector<std::string> events;

  EXPECT_THROW((void)PartiallyConstructedOwner{events}, DomainFailure);
  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "construct first",
          "construct second",
          "destroy first",
      }));

  // second 的构造没有完成，所以不会调用它的析构；已经完成的 first 会被销毁。
  // 最外层对象本身从未完成构造，其析构函数也不会执行。
}

TEST(Noexcept, OperatorAndTraitsObserveTheExceptionSpecification) {
  static_assert(noexcept(guaranteed_no_throw()));
  static_assert(!noexcept(potentially_throwing()));
  static_assert(std::is_nothrow_invocable_v<decltype(guaranteed_no_throw)>);
  static_assert(!std::is_nothrow_invocable_v<decltype(potentially_throwing)>);

  using NoThrowPointer = void (*)() noexcept;
  NoThrowPointer function = guaranteed_no_throw;
  function();
  SUCCEED();

  // C++17 起 noexcept 属于函数类型的一部分；不抛函数指针可以转换到可能抛的类型，
  // 反向不行。若 noexcept 函数仍让异常逃出，运行时调用 terminate，而不是普通传播。
}

TEST(ExceptionSafety, CommitAfterAllWorkProvidesTheStrongGuarantee) {
  TransactionalValue value{{1, 2}};

  EXPECT_THROW(value.append_two_or_rollback(3, 4, true), DomainFailure);
  EXPECT_EQ(value.values(), (std::vector<int>{1, 2}));

  EXPECT_NO_THROW(value.append_two_or_rollback(3, 4, false));
  EXPECT_EQ(value.values(), (std::vector<int>{1, 2, 3, 4}));

  // 先在临时副本完成所有可能失败的工作，最后用不抛的 swap 提交，失败时原对象不变。
  // 这是 strong exception guarantee 的常见 transaction/commit 实现方式。
}

}  // namespace
