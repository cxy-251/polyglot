// 横向概念 004｜同步资源清理、异常安全与清理冲突。
// 共同问题：正常退出是否清理；异常退出是否清理；多个资源是否逆序清理；
// 清理由什么机制触发；清理失败与原始异常如何交互。
//
// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp

#include <gtest/gtest.h>

#include <exception>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class BodyFailure : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

class RecordingResource {
 public:
  RecordingResource(std::vector<std::string>& events, std::string name)
      : events_(events), name_(std::move(name)) {
    events_.push_back("acquire:" + name_);
  }

  ~RecordingResource() noexcept {
    const std::string exit_kind =
        std::uncaught_exceptions() == 0 ? ":normal" : ":unwinding";
    events_.push_back("release:" + name_ + exit_kind);
  }

  [[nodiscard]] const std::string& name() const noexcept { return name_; }

 private:
  std::vector<std::string>& events_;
  std::string name_;
};

TEST(ResourceCleanupConcept, AutomaticObjectCleansOnNormalScopeExit) {
  std::vector<std::string> events;

  {
    RecordingResource resource{events, "normal"};
    EXPECT_EQ(resource.name(), "normal");
    events.push_back("body");
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "acquire:normal",
          "body",
          "release:normal:normal",
      }));
}

TEST(ResourceCleanupConcept, StackUnwindingCleansBeforeTheHandlerRuns) {
  std::vector<std::string> events;

  try {
    RecordingResource resource{events, "exception"};
    events.push_back("body");
    throw BodyFailure{"body failed"};
  } catch (const BodyFailure& error) {
    events.push_back(std::string{"caught:"} + error.what());
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "acquire:exception",
          "body",
          "release:exception:unwinding",
          "caught:body failed",
      }));
}

TEST(ResourceCleanupConcept, AutomaticObjectsCleanInReverseConstructionOrder) {
  std::vector<std::string> events;

  {
    RecordingResource first{events, "first"};
    RecordingResource second{events, "second"};
    events.push_back("body");
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "acquire:first",
          "acquire:second",
          "body",
          "release:second:normal",
          "release:first:normal",
      }));
}

TEST(ResourceCleanupConcept, NoThrowDestructorPreservesTheOriginalExceptionPath) {
  static_assert(std::is_nothrow_destructible_v<RecordingResource>);
  static_assert(noexcept(std::declval<RecordingResource&>().~RecordingResource()));
  static_assert(
      std::is_same_v<
          decltype(std::declval<RecordingResource&>().~RecordingResource()),
          void>);

  // 析构函数没有 Python __exit__ 那样的异常参数或真假返回通道，不能决定抑制原异常。
  // 若栈展开直接调用的析构函数又让异常逃出，标准要求 std::terminate；这里不执行该危险路径。
  SUCCEED();
}

}  // namespace
