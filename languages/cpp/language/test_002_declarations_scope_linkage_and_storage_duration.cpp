// polyglot-covers:
// - cpp.language.declarations-and-definitions
// - cpp.language.scope-and-name-hiding
// - cpp.language.internal-external-and-inline-linkage
// - cpp.language.automatic-static-thread-and-dynamic-storage-duration
// - cpp.language.block-static-initialization

// 跨语言迁移提示：C++ 把作用域、链接和存储期分成不同维度；Python 与 JavaScript
// 的名字可见性不能直接推导对象寿命，C++ 的按引用捕获还可能在作用域结束后悬空。

#include <gtest/gtest.h>

#include <array>
#include <cstdint>
#include <string>
#include <thread>
#include <vector>

namespace linkage_examples {

extern int declared_counter;
int declared_counter = 11;

// namespace 作用域的非 volatile const 对象默认具有内部链接；加 extern 可显式获得
// 外部链接。inline constexpr 则适合在头文件中给多个翻译单元提供同一个实体。
const int internal_constant = 13;
extern const int external_constant = 17;
inline constexpr int inline_header_constant = 19;

}  // namespace linkage_examples

namespace {

int namespace_value = 5;
thread_local int per_thread_value = -1;
int static_construction_count = 0;

class StaticRecord {
 public:
  StaticRecord() { ++static_construction_count; }

  int value{41};
};

StaticRecord& function_local_static() {
  // 初始化发生在控制流第一次经过声明时。C++11 起，并发首次调用也必须只初始化一次。
  static StaticRecord record;
  return record;
}

class ScopeOwner {
 public:
  explicit ScopeOwner(int value) : value_(value) {}

  [[nodiscard]] int value() const { return value_; }
  [[nodiscard]] static int category() { return category_; }

 private:
  int value_;
  inline static int category_{23};
};

class LifetimeLog {
 public:
  LifetimeLog(std::vector<std::string>& events, std::string name)
      : events_(events), name_(std::move(name)) {
    events_.push_back("construct " + name_);
  }

  ~LifetimeLog() { events_.push_back("destroy " + name_); }

 private:
  std::vector<std::string>& events_;
  std::string name_;
};

TEST(Declarations, AnExternDeclarationAndDefinitionNameOneEntity) {
  EXPECT_EQ(linkage_examples::declared_counter, 11);
  linkage_examples::declared_counter += 1;
  EXPECT_EQ(linkage_examples::declared_counter, 12);

  EXPECT_EQ(linkage_examples::internal_constant, 13);
  EXPECT_EQ(linkage_examples::external_constant, 17);
  EXPECT_EQ(linkage_examples::inline_header_constant, 19);

  // extern 声明本身通常不分配对象；后面的定义才提供存储。一个程序中可有许多兼容
  // 声明，但受 ODR 约束的非 inline 实体只能有一个程序级定义。
}

TEST(Scope, InnerDeclarationsHideRatherThanReplaceOuterNames) {
  int namespace_value = 7;
  EXPECT_EQ(namespace_value, 7);
  EXPECT_EQ(::namespace_value, 5);

  {
    int namespace_value = 9;
    EXPECT_EQ(namespace_value, 9);
    EXPECT_EQ(::namespace_value, 5);
  }

  EXPECT_EQ(namespace_value, 7);

  // 每个声明区域决定名字从哪里开始可见。离开内层 block 后，外层名字重新成为
  // 非限定查找结果；对象本身没有因为同名声明而被修改。
}

TEST(Scope, ClassMembersHaveClassScopeAndNeedAnObjectUnlessStatic) {
  ScopeOwner first{31};
  ScopeOwner second{37};

  EXPECT_EQ(first.value(), 31);
  EXPECT_EQ(second.value(), 37);
  EXPECT_EQ(ScopeOwner::category(), 23);

  // 非 static 数据成员属于每个对象，static 数据成员属于类所表示的共享实体。
  // inline static 允许直接在类定义中给出定义，避免另写一个翻译单元级定义。
}

TEST(StorageDuration, AutomaticObjectsAreDestroyedInReverseConstructionOrder) {
  std::vector<std::string> events;

  {
    LifetimeLog first{events, "first"};
    LifetimeLog second{events, "second"};
    EXPECT_EQ(events, (std::vector<std::string>{"construct first", "construct second"}));
  }

  EXPECT_EQ(
      events,
      (std::vector<std::string>{
          "construct first",
          "construct second",
          "destroy second",
          "destroy first",
      }));

  // block 内自动存储期对象按构造完成顺序的逆序析构，这正是 RAII 能可靠释放嵌套
  // 资源的基础；提前 return 或抛出异常时也遵守相同的栈展开规则。
}

TEST(StorageDuration, FunctionLocalStaticIsInitializedOnlyOnce) {
  StaticRecord& first = function_local_static();
  StaticRecord& second = function_local_static();

  EXPECT_EQ(&first, &second);
  EXPECT_EQ(static_construction_count, 1);

  first.value = 43;
  EXPECT_EQ(second.value, 43);

  // static 存储期不等于“不可变”。对象一直存活到程序终止，但共享可变状态仍需考虑
  // 并发同步、测试隔离和初始化依赖；局部 static 只保证初始化过程是线程安全的。
}

TEST(StorageDuration, ThreadLocalCreatesOneObjectForEachThread) {
  per_thread_value = 100;

  std::array<std::uintptr_t, 2> addresses{};
  std::array<int, 2> observed_values{};

  auto worker = [&](std::size_t index, int value) {
    per_thread_value = value;
    addresses[index] = reinterpret_cast<std::uintptr_t>(&per_thread_value);
    observed_values[index] = per_thread_value;
  };

  std::thread first{worker, 0U, 201};
  std::thread second{worker, 1U, 202};
  first.join();
  second.join();

  EXPECT_EQ(observed_values, (std::array<int, 2>{201, 202}));
  EXPECT_NE(addresses[0], addresses[1]);
  EXPECT_EQ(per_thread_value, 100);

  // thread_local 名字相同，但每个线程访问自己的对象。对象地址和状态都不同；
  // 线程退出时，其具有非平凡析构函数的 thread_local 对象才会析构。
}

}  // namespace
