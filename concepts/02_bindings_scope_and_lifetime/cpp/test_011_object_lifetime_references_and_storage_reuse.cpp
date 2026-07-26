// polyglot-covers:
// - cpp.language.pointer-and-reference-semantics
// - cpp.language.one-past-array-pointer
// - cpp.language.temporary-lifetime-extension
// - cpp.language.full-expression-destruction
// - cpp.language.dynamic-storage-new-and-delete
// - cpp.language.placement-new-storage-reuse-and-launder
// - cpp.language.dangling-reference-traps

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <new>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class TemporaryProbe {
 public:
  TemporaryProbe(std::vector<std::string>& events, std::string name)
      : events_(events), name_(std::move(name)) {
    events_.push_back("construct " + name_);
  }

  ~TemporaryProbe() { events_.push_back("destroy " + name_); }

  [[nodiscard]] int value() const { return 7; }

 private:
  std::vector<std::string>& events_;
  std::string name_;
};

struct ImmutableRecord {
  const int value;
};

TEST(References, AssignmentThroughAReferenceDoesNotReseatIt) {
  int first = 3;
  int second = 9;
  int& alias = first;

  alias = second;

  EXPECT_EQ(first, 9);
  EXPECT_EQ(second, 9);
  EXPECT_EQ(&alias, &first);

  // 引用初始化后始终指代同一对象；`alias = second` 调用的是 int 赋值，不是把 alias
  // 改绑到 second。需要可空或可重新指向的关系时，应使用指针或显式包装类型。
}

TEST(Pointers, OnePastPointerSupportsIterationButNotDereference) {
  std::array<int, 3> values{2, 3, 5};
  int* begin = values.data();
  int* end = begin + values.size();

  int sum = 0;
  for (int* current = begin; current != end; ++current) {
    sum += *current;
  }

  EXPECT_EQ(sum, 10);
  EXPECT_EQ(end - begin, 3);

  // 同一数组允许形成和比较 one-past 指针，这正是半开区间 [begin, end) 的基础；
  // end 本身不指向对象，解引用它仍是未定义行为。跨无关数组做减法也没有定义。
}

TEST(TemporaryLifetime, LocalConstReferenceExtendsATemporaryObject) {
  const std::string& text = std::string{"extended"};
  EXPECT_EQ(text, "extended");

  std::string&& rvalue_reference = std::string{"also extended"};
  EXPECT_EQ(rvalue_reference, "also extended");

  // 直接绑定局部引用的临时量通常延长到引用作用域结束。这个规则不会沿引用继续传递：
  // 返回引用的函数如果把参数绑定到调用方临时量，完整表达式结束后仍会悬空。
}

TEST(TemporaryLifetime, UnboundTemporaryDiesAtTheEndOfTheFullExpression) {
  std::vector<std::string> events;

  int result = TemporaryProbe{events, "operand"}.value();
  EXPECT_EQ(result, 7);
  EXPECT_EQ(
      events,
      (std::vector<std::string>{"construct operand", "destroy operand"}));

  // 临时对象一直活到包含它的 full-expression 结束，而不是在成员函数返回的瞬间销毁。
  // 逗号、条件和函数实参中的临时量也遵守各自完整表达式边界。
}

TEST(DynamicStorage, NewAndDeleteMustUseMatchingArrayForms) {
  int* scalar = new int{41};
  int* sequence = new int[3]{2, 3, 5};

  EXPECT_EQ(*scalar, 41);
  EXPECT_EQ(sequence[0] + sequence[1] + sequence[2], 10);

  delete scalar;
  delete[] sequence;

  // new-expression 同时取得存储并开始对象生命周期；delete-expression 先析构再释放。
  // new[] 必须匹配 delete[]。真实所有权优先交给容器或智能指针，避免异常路径泄漏。
}

TEST(ObjectLifetime, PlacementNewCanStartANewLifetimeInExistingStorage) {
  alignas(ImmutableRecord) std::byte storage[sizeof(ImmutableRecord)];

  auto* first = ::new (static_cast<void*>(storage)) ImmutableRecord{7};
  EXPECT_EQ(first->value, 7);
  first->~ImmutableRecord();

  ::new (static_cast<void*>(storage)) ImmutableRecord{11};
  ImmutableRecord* current = std::launder(first);
  EXPECT_EQ(current->value, 11);
  current->~ImmutableRecord();

  // placement new 不分配内存，只在给定存储中开始新对象生命周期。旧对象含 const 成员，
  // 重建后通过旧指针观察新对象要使用 std::launder；每次成功构造也必须恰好析构一次。
}

TEST(ObjectLifetime, TypePropertiesDoNotMakeDanglingAccessSafe) {
  static_assert(std::is_trivially_destructible_v<int>);
  static_assert(std::is_trivially_copyable_v<int>);

  int value = 13;
  int* pointer = &value;
  EXPECT_EQ(*pointer, 13);

  // 即使类型 trivially destructible，指针也只在对象生命周期内可解引用。返回局部变量
  // 地址、保存容器扩容前的迭代器，或捕获已销毁对象的引用都会产生悬空访问。
}

}  // namespace
