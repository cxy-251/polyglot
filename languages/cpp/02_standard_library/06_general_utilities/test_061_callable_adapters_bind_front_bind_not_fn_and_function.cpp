// polyglot-covers:
// - cpp.stdlib.functional.not-fn
// - cpp.stdlib.functional.bind-front
// - cpp.stdlib.functional.bind-front-decayed-state-and-rvalue-invocation
// - cpp.stdlib.functional.bind-placeholders-and-reference-binding
// - cpp.stdlib.functional.is-bind-expression-and-is-placeholder
// - cpp.stdlib.functional.function-empty-state-and-bad-function-call
// - cpp.stdlib.functional.function-type-erased-call-signature
// - cpp.stdlib.functional.function-copy-and-reference-wrapper-state
// - cpp.stdlib.functional.function-target-type-and-target
// - cpp.stdlib.functional.function-swap-and-null-assignment

#include <gtest/gtest.h>

#include <functional>
#include <memory>
#include <string>
#include <type_traits>
#include <typeinfo>
#include <utility>

namespace {

struct Multiplier {
  int factor;
  int operator()(int value) const { return factor * value; }
};

struct SharedCounter {
  int value = 0;
  int operator()() { return ++value; }
};

std::string join_number_and_text(int number, const std::string& text) {
  return std::to_string(number) + ":" + text;
}

TEST(NotFn, NegatesTheBooleanTestOfAnyInvocable) {
  const auto odd = [](int value) { return value % 2 != 0; };
  const auto even = std::not_fn(odd);
  const auto not_empty = std::not_fn(&std::string::empty);

  EXPECT_TRUE(even(4));
  EXPECT_FALSE(even(5));
  EXPECT_TRUE(not_empty(std::string{"data"}));
  EXPECT_FALSE(not_empty(std::string{}));

  // not_fn 保存 decay 后的 callable，调用时转发实参并对 INVOKE 结果施加 !。
  // 它不要求结果精确是 bool，只要 operator! 合法；这也意味着自定义 ! 的语义会被原样保留。
}

TEST(BindFront, StoresLeadingArgumentsAndAppendsCallTimeArguments) {
  int base = 10;
  auto add_to_base = std::bind_front(
      [](int& target, int first, int second) {
        target += first + second;
        return target;
      },
      std::ref(base),
      3);

  EXPECT_EQ(add_to_base(4), 17);
  EXPECT_EQ(base, 17);

  auto consume_once = std::bind_front(
      [](std::unique_ptr<int> owned, int extra) {
        return *owned + extra;
      },
      std::make_unique<int>(40));

  static_assert(!std::is_invocable_v<decltype(consume_once)&, int>);
  static_assert(std::is_invocable_v<decltype(consume_once)&&, int>);
  EXPECT_EQ(std::move(consume_once)(2), 42);

  // bound arguments 默认 decay 后按值保存，需别名必须显式 std::ref。调用 lvalue
  // wrapper 会把存储状态当 lvalue；只有 std::move(wrapper) 才能把内部 unique_ptr 移入按值参数。
}

TEST(Bind, PlaceholdersReorderCallArgumentsAndRefPreservesAliasing) {
  using namespace std::placeholders;

  auto reorder = std::bind(join_number_and_text, _2, _1);
  EXPECT_EQ(reorder(std::string{"item"}, 7), "7:item");

  int state = 5;
  auto by_value = std::bind(std::plus<>{}, state, _1);
  auto by_reference = std::bind(
      [](int& target, int delta) { return target += delta; },
      std::ref(state),
      _1);
  state = 10;

  EXPECT_EQ(by_value(2), 7);
  EXPECT_EQ(by_reference(3), 13);
  EXPECT_EQ(state, 13);
  static_assert(std::is_bind_expression_v<decltype(reorder)>);
  static_assert(std::is_placeholder_v<decltype(_1)> == 1);
  static_assert(std::is_placeholder_v<decltype(_2)> == 2);

  // bind 的 placeholder 按调用时位置取实参，可重排或复用；普通 bound value
  // 在绑定时就被 decay-copy。复用同一 placeholder 传入 rvalue 可能导致多次移动，应避免这种隐蔽接口。
}

TEST(Function, EmptyWrapperReportsFalseAndThrowsWhenCalled) {
  std::function<int(int)> callback;

  EXPECT_FALSE(static_cast<bool>(callback));
  EXPECT_EQ(callback, nullptr);
  EXPECT_EQ(callback.target_type(), typeid(void));
  EXPECT_THROW((void)callback(3), std::bad_function_call);

  // 空 function 没有 target，operator bool 用于调用前检查；直接调用会抛
  // bad_function_call，不是返回默认 R。target_type() 对空 wrapper 与 any 一样返回 typeid(void)。
}

TEST(Function, OneSignatureErasesDifferentCopyableCallableTypes) {
  std::function<int(int)> operation = Multiplier{3};
  EXPECT_EQ(operation(4), 12);

  operation = [](int value) { return value + 1; };
  EXPECT_EQ(operation(4), 5);

  int (*square)(int) = +[](int value) { return value * value; };
  operation = square;
  EXPECT_EQ(operation(5), 25);

  // std::function<R(Args...)> 擦除具体 callable type，只保留可调用签名。目标必须
  // CopyConstructible，因为 function 本身是可复制值类型；捕获 unique_ptr 的
  // move-only lambda 不能直接存入 C++20 std::function。
}

TEST(Function, CopyingAStoredCallableCopiesItsCurrentState) {
  std::function<int()> first = [count = 0]() mutable { return ++count; };
  EXPECT_EQ(first(), 1);

  std::function<int()> copied = first;
  EXPECT_EQ(first(), 2);
  EXPECT_EQ(copied(), 2);
  EXPECT_EQ(copied(), 3);
  EXPECT_EQ(first(), 3);

  // function 复制会复制当时的 callable 状态。copied 从 count==1 开始，但之后
  // 与 first 独立递增；若期望多个 callback 共享状态，应显式存 reference_wrapper 或共享所有权对象。
}

TEST(Function, ReferenceWrapperMakesCopiesShareTheOriginalCallable) {
  SharedCounter counter;
  std::function<int()> first = std::ref(counter);
  std::function<int()> second = first;

  EXPECT_EQ(first(), 1);
  EXPECT_EQ(second(), 2);
  EXPECT_EQ(counter.value, 2);

  // 存入 reference_wrapper 是 std::function 的特殊支持路径：复制 wrapper 仍指向原 callable，
  // 不复制状态。function 不管理 counter 寿命，所以这种别名不能逃离 counter 的有效作用域。
}

TEST(Function, TargetInspectionRequiresTheExactStoredCallableType) {
  std::function<int(int)> operation = Multiplier{4};

  EXPECT_EQ(operation.target_type(), typeid(Multiplier));
  Multiplier* multiplier = operation.target<Multiplier>();
  ASSERT_NE(multiplier, nullptr);
  EXPECT_EQ(multiplier->factor, 4);
  EXPECT_EQ(operation.target<int (*)(int)>(), nullptr);

  multiplier->factor = 5;
  EXPECT_EQ(operation(6), 30);

  // target<T>() 只在 T 与存储的具体类型精确相同时返回指针，不会做签名兼容转换。
  // 它暴露的是 wrapper 内部对象，修改会改变之后调用；常规业务不应依赖这个逃生口破坏类型擦除。
}

TEST(Function, SwapAndNullAssignmentReplaceTargetsWithoutCallingThem) {
  std::function<int(int)> increment = [](int value) { return value + 1; };
  std::function<int(int)> double_value = [](int value) { return value * 2; };

  increment.swap(double_value);
  EXPECT_EQ(increment(5), 10);
  EXPECT_EQ(double_value(5), 6);

  double_value = nullptr;
  EXPECT_FALSE(double_value);
  EXPECT_THROW((void)double_value(5), std::bad_function_call);

  // swap 只交换 target，不调用它们；赋 nullptr 销毁现有 target 并返回空状态。
  // 这是取消 callback 的明确方式，不需要约定一个“什么也不做”的特殊 lambda。
}

}  // namespace
