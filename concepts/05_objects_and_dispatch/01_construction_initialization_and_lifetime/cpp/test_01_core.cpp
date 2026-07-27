// 对象构造、初始化与生命周期。
// 共同问题：分配与初始化能否分开；复制是否自动发生；销毁时机是否确定；
// 类型如何定制创建结果。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: construction_initialization_and_lifetime
// polyglot-related: languages/cpp/language/test_008_classes_construction_and_special_members.cpp
// polyglot-related: languages/cpp/language/test_011_object_lifetime_references_and_storage_reuse.cpp

#include <gtest/gtest.h>

#include <algorithm>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct Record {
  std::vector<std::string>* events;
  std::string name;

  Record(std::vector<std::string>& log, std::string value)
      : events(&log), name(std::move(value)) {
    events->push_back("construct:" + name);
  }

  Record(const Record& other) : events(other.events), name(other.name + ":copy") {
    events->push_back("copy:" + name);
  }

  Record(Record&& other) noexcept : events(other.events), name(std::move(other.name)) {
    events->push_back("move:" + name);
  }

  ~Record() {
    events->push_back("destroy:" + name);
  }
};

TEST(ObjectLifetimeConcept, ConstructorStartsLifetimeAndDestructorEndsAtScopeExit) {
  std::vector<std::string> events;
  {
    Record record{events, "value"};
    EXPECT_EQ(record.name, "value");
  }

  EXPECT_EQ(events, (std::vector<std::string>{"construct:value", "destroy:value"}));

  // 自动对象按作用域确定销毁；Python/JavaScript 的垃圾回收对象没有同等析构时点。
}

TEST(ObjectLifetimeConcept, CopyAndMoveAreDistinctLanguageOperations) {
  std::vector<std::string> events;
  {
    Record original{events, "value"};
    Record copied = original;
    Record moved = std::move(original);
    EXPECT_EQ(copied.name, "value:copy");
    EXPECT_EQ(moved.name, "value");
  }

  EXPECT_NE(std::find(events.begin(), events.end(), "copy:value:copy"), events.end());
  EXPECT_NE(std::find(events.begin(), events.end(), "move:value"), events.end());
}

TEST(ObjectLifetimeConcept, TypeCanForbidCopyAtCompileTime) {
  struct Unique {
    Unique() = default;
    Unique(const Unique&) = delete;
    Unique& operator=(const Unique&) = delete;
  };

  static_assert(!std::is_copy_constructible_v<Unique>);
  static_assert(!std::is_copy_assignable_v<Unique>);
}

}  // namespace
