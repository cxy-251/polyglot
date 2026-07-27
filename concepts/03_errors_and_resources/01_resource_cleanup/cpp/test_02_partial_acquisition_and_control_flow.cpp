// 资源部分取得失败与控制流退出。
// 共同问题：后续资源取得失败时已取得资源是否清理；return 是否绕过清理；
// 清理责任何时登记，尚未成功取得的资源是否参与释放。
//
// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/cpp/language/test_012_exceptions_raii_and_noexcept.cpp

#include <gtest/gtest.h>

#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Resource {
  Resource(std::vector<std::string>& log, std::string resource_name)
      : events(log), name(std::move(resource_name)) {
    events.push_back("construct:" + name);
  }

  ~Resource() {
    events.push_back("destroy:" + name);
  }

  std::vector<std::string>& events;
  std::string name;
};

struct FailingMember {
  explicit FailingMember(std::vector<std::string>& events) {
    events.push_back("construct:second");
    throw std::runtime_error{"cannot acquire second"};
  }
};

struct Owner {
  explicit Owner(std::vector<std::string>& events)
      : first(events, "first"), second(events) {}

  Resource first;
  FailingMember second;
};

int return_from_scope(std::vector<std::string>& events) {
  Resource resource{events, "value"};
  events.push_back("return");
  return 42;
}

TEST(PartialAcquisitionConcept, ConstructedMembersCleanWhenALaterMemberThrows) {
  std::vector<std::string> events;

  EXPECT_THROW(static_cast<void>(Owner{events}), std::runtime_error);

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "construct:first",
          "construct:second",
          "destroy:first",
      }));

  // second 的构造未完成，所以其析构不运行；已完成的 first 在构造函数异常路径自动析构。
}

TEST(PartialAcquisitionConcept, ReturnDestroysAutomaticObjectsBeforeCallerObservesValue) {
  std::vector<std::string> events;

  const int result = return_from_scope(events);

  EXPECT_EQ(result, 42);
  EXPECT_EQ(
      events,
      (std::vector<std::string>{"construct:value", "return", "destroy:value"}));
}

}  // namespace
