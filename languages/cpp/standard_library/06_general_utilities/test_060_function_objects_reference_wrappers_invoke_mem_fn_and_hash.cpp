// polyglot-covers:
// - cpp.stdlib.functional.reference-wrapper-ref-and-cref
// - cpp.stdlib.functional.reference-wrapper-callable-forwarding
// - cpp.stdlib.functional.invoke-functions-members-and-reference-wrappers
// - cpp.stdlib.functional.mem-fn
// - cpp.stdlib.functional.arithmetic-comparison-logical-and-bitwise-objects
// - cpp.stdlib.functional.transparent-function-objects
// - cpp.stdlib.functional.identity
// - cpp.stdlib.functional.hash-contract-and-custom-specialization

#include <gtest/gtest.h>

#include <functional>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>

namespace hash_example {

struct UserId {
  int tenant;
  int local;

  friend bool operator==(const UserId&, const UserId&) = default;
};

}  // namespace hash_example

template <>
struct std::hash<hash_example::UserId> {
  std::size_t operator()(const hash_example::UserId& id) const noexcept {
    const std::size_t first = std::hash<int>{}(id.tenant);
    const std::size_t second = std::hash<int>{}(id.local);
    return first ^ (second + 0x9e3779b9U + (first << 6U) + (first >> 2U));
  }
};

namespace {

class Accumulator {
 public:
  int add(int amount) {
    total += amount;
    return total;
  }

  int read() const { return total; }

  int total = 0;
};

struct StatefulCallable {
  int calls = 0;

  int operator()(int value) {
    ++calls;
    return value * 2;
  }
};

template <typename FunctionObject>
concept Transparent = requires { typename FunctionObject::is_transparent; };

TEST(ReferenceWrapper, RefAndCrefStoreCopyableNonOwningReferences) {
  int value = 3;
  std::reference_wrapper<int> mutable_reference = std::ref(value);
  std::reference_wrapper<const int> const_reference = std::cref(value);

  static_assert(std::is_copy_constructible_v<decltype(mutable_reference)>);
  mutable_reference.get() = 8;

  EXPECT_EQ(value, 8);
  EXPECT_EQ(const_reference.get(), 8);
  EXPECT_EQ(&mutable_reference.get(), &value);

  // reference_wrapper 把 T& 包装成可复制、可赋值的普通对象，但仍不拥有 T。
  // std::ref/std::cref 只接受可安全引用的 lvalue，rvalue overload 被删除，以减少立即悬空的封装。
}

TEST(ReferenceWrapper, CallableWrapperForwardsCallsToTheOriginalObject) {
  StatefulCallable callable;
  auto wrapper = std::ref(callable);
  auto copied_wrapper = wrapper;

  EXPECT_EQ(wrapper(4), 8);
  EXPECT_EQ(copied_wrapper(5), 10);
  EXPECT_EQ(callable.calls, 2);

  // reference_wrapper 对可调用 T 提供 operator()，内部按 std::invoke 规则调用
  // 原对象。复制 wrapper 只复制别名，两个 wrapper 共享同一个 calls 状态，不会复制 callable。
}

TEST(Invoke, UniformlyCallsFunctionsMemberFunctionsAndDataMembers) {
  const auto multiply = [](int left, int right) { return left * right; };
  Accumulator accumulator;

  EXPECT_EQ(std::invoke(multiply, 6, 7), 42);
  EXPECT_EQ(std::invoke(&Accumulator::add, accumulator, 5), 5);
  EXPECT_EQ(
      std::invoke(&Accumulator::add, std::ref(accumulator), 4),
      9);

  int& data_member = std::invoke(&Accumulator::total, &accumulator);
  data_member = 12;
  EXPECT_EQ(accumulator.read(), 12);

  // invoke 不只是 function-call syntax 包装：对成员指针它还识别对象、指针和
  // reference_wrapper。调用 data member pointer 返回对应成员引用，所以这里可直接赋值。
}

TEST(MemFn, TurnsAMemberPointerIntoAReusableCallWrapper) {
  Accumulator accumulator;
  auto add = std::mem_fn(&Accumulator::add);
  auto total = std::mem_fn(&Accumulator::total);

  EXPECT_EQ(add(accumulator, 3), 3);
  total(accumulator) = 10;
  EXPECT_EQ(add(&accumulator, 2), 12);

  // mem_fn 把成员指针变成可复制的普通 function object，调用时仍使用 INVOKE
  // 对象规则。data member 版本保留引用返回值，不会把成员悄悄复制出来。
}

TEST(StandardFunctionObjects, CoverOperatorFamiliesWithoutCustomLambdas) {
  EXPECT_EQ(std::plus<>{}(2, 3.5), 5.5);
  EXPECT_EQ(std::minus<>{}(9, 4), 5);
  EXPECT_EQ(std::multiplies<>{}(6, 7), 42);
  EXPECT_EQ(std::divides<>{}(12, 3), 4);
  EXPECT_EQ(std::modulus<>{}(13, 5), 3);
  EXPECT_EQ(std::negate<>{}(8), -8);

  EXPECT_TRUE(std::equal_to<>{}(3, 3L));
  EXPECT_TRUE(std::less<>{}(2, 3.0));
  EXPECT_TRUE(std::logical_and<>{}(true, 1));
  EXPECT_EQ(std::bit_xor<>{}(0b1100, 0b1010), 0b0110);

  // void specialization 如 plus<> 和 less<> 使用实参推导运算类型，可处理异构参数；
  // plus<int> 则会先把两边转为 int。它们保留对应运算符的语义和陷阱，不额外检查除零。
}

TEST(TransparentFunctionObjects, ExposeIsTransparentForHeterogeneousLookup) {
  static_assert(Transparent<std::less<>>);
  static_assert(!Transparent<std::less<int>>);
  EXPECT_TRUE(std::less<>{}(2, 3L));
  EXPECT_TRUE(std::equal_to<>{}(std::string_view{"id"}, std::string{"id"}));

  // is_transparent 是关联容器用来启用异构 find 等 overload 的标记，自身没有值。
  // 它表示 functor 不把参数强制转为固定 T，但具体两个类型的运算符仍必须本来就合法。
}

TEST(Identity, PerfectlyForwardsItsArgumentInsteadOfMakingAValueCopy) {
  int value = 14;
  const int constant = 15;

  static_assert(
      std::is_same_v<decltype(std::identity{}(value)), int&>);
  static_assert(
      std::is_same_v<decltype(std::identity{}(constant)), const int&>);

  std::identity{}(value) = 20;
  EXPECT_EQ(value, 20);

  // identity 是通用算法的默认 projection：返回 std::forward<T>(value)，保留
  // cv/ref 和值类别。它不是“复制一份原值”，因此对 lvalue 的结果赋值会修改原对象。
}

TEST(Hash, EqualKeysMustHashEquallyButTheNumericRecipeIsNotPersistentData) {
  const hash_example::UserId first{3, 17};
  const hash_example::UserId same{3, 17};
  const hash_example::UserId other{3, 18};
  const std::hash<hash_example::UserId> hasher;

  EXPECT_EQ(first, same);
  EXPECT_EQ(hasher(first), hasher(same));
  EXPECT_NE(first, other);

  const std::string text = "stable equality";
  EXPECT_EQ(std::hash<std::string>{}(text), std::hash<std::string>{}(text));

  // 对用户类型可在 std 中显式特化 hash，必须保证 a == b 则 hash(a) == hash(b)。
  // 反向不成立，碰撞完全合法；标准也不保证数值跨进程、平台或库版本稳定，不应持久化。
}

}  // namespace
