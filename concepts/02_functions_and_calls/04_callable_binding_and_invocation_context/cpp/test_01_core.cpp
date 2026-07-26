// 可调用对象绑定与调用上下文。
// 共同问题：成员函数如何获得接收者；提取函数后是否保留接收者；如何显式调用；
// 语言是否允许固定或替换调用上下文。
//
// polyglot-family: functions_and_calls
// polyglot-concept: callable_binding_and_invocation_context
// polyglot-related: languages/cpp/language/test_034_class_members_ref_qualifiers_and_member_pointers.cpp

#include <gtest/gtest.h>

#include <functional>
#include <type_traits>

namespace {

class Counter {
 public:
  explicit Counter(int value) : value_(value) {}

  int add(int amount) const {
    return value_ + amount;
  }

 private:
  int value_;
};

TEST(InvocationContextConcept, MemberPointerDoesNotContainAnObject) {
  auto member = &Counter::add;
  Counter counter{10};

  static_assert(std::is_member_function_pointer_v<decltype(member)>);
  EXPECT_EQ((counter.*member)(2), 12);
  EXPECT_EQ(std::invoke(member, counter, 3), 13);
}

TEST(InvocationContextConcept, InvokeAcceptsReferenceOrPointerReceivers) {
  Counter counter{10};
  Counter* pointer = &counter;

  EXPECT_EQ(std::invoke(&Counter::add, counter, 1), 11);
  EXPECT_EQ(std::invoke(&Counter::add, pointer, 2), 12);
  EXPECT_EQ(std::invoke(&Counter::add, std::ref(counter), 3), 13);
}

TEST(InvocationContextConcept, LambdaCanBindAReceiverExplicitly) {
  Counter first{10};
  Counter second{20};
  auto stored = [&first](int amount) { return first.add(amount); };

  EXPECT_EQ(stored(1), 11);
  EXPECT_EQ(second.add(1), 21);

  // C++ 成员指针不会像 Python bound method 自动拥有对象；lambda/bind_front 可显式组合。
}

TEST(InvocationContextConcept, StaticInvocabilityCanRejectMissingReceiver) {
  using Member = int (Counter::*)(int) const;

  static_assert(std::is_invocable_v<Member, Counter&, int>);
  static_assert(!std::is_invocable_v<Member, int>);
}

}  // namespace
