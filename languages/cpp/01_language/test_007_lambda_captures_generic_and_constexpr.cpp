// polyglot-covers:
// - cpp.language.lambda-closure-types
// - cpp.language.lambda-copy-reference-and-init-capture
// - cpp.language.mutable-lambda
// - cpp.language.this-and-star-this-capture
// - cpp.language.generic-lambda-template-parameters
// - cpp.language.captureless-lambda-function-pointer
// - cpp.language.constexpr-lambda

#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <type_traits>
#include <utility>

namespace {

class Multiplier {
 public:
  explicit Multiplier(int factor) : factor_(factor) {}

  void set_factor(int factor) { factor_ = factor; }

  auto live_view() { return [this](int value) { return value * factor_; }; }
  auto snapshot() { return [*this](int value) { return value * factor_; }; }

 private:
  int factor_;
};

TEST(Lambdas, CopyCaptureTakesASnapshotWhileReferenceCaptureTracksTheObject) {
  int value = 3;
  auto by_value = [value] { return value; };
  auto by_reference = [&value] { return value; };

  value = 9;

  EXPECT_EQ(by_value(), 3);
  EXPECT_EQ(by_reference(), 9);

  // copy capture 在闭包创建时初始化成员，reference capture 保存别名。返回或异步保存
  // 引用捕获闭包前，必须保证被引用对象活得更久，否则调用闭包会访问悬空引用。
}

TEST(Lambdas, MutableChangesTheCapturedCopyNotTheOriginal) {
  int original = 10;
  auto counter = [state = original]() mutable {
    ++state;
    return state;
  };

  EXPECT_EQ(counter(), 11);
  EXPECT_EQ(counter(), 12);
  EXPECT_EQ(original, 10);

  // lambda 的 operator() 默认是 const，因此普通值捕获成员不能修改。mutable 移除这个
  // const 限制，但修改的仍是闭包内部副本，不会把捕获方式变成引用。
}

TEST(Lambdas, InitCaptureCanTransferMoveOnlyOwnership) {
  auto owner = std::make_unique<std::string>("owned");
  auto reader = [owned = std::move(owner)] { return *owned; };

  EXPECT_EQ(owner, nullptr);
  EXPECT_EQ(reader(), "owned");
  static_assert(!std::is_copy_constructible_v<decltype(reader)>);
  static_assert(std::is_move_constructible_v<decltype(reader)>);

  // init-capture 相当于声明一个闭包成员，可以改名、计算或移动初始化。成员是 unique_ptr
  // 时闭包也成为 move-only；把它交给要求可复制回调的旧接口会在编译期失败。
}

TEST(Lambdas, ThisCaptureObservesTheObjectWhileStarThisCopiesIt) {
  Multiplier multiplier{3};
  auto live = multiplier.live_view();
  auto snapshot = multiplier.snapshot();

  multiplier.set_factor(5);

  EXPECT_EQ(live(4), 20);
  EXPECT_EQ(snapshot(4), 12);

  // [this] 捕获指针，不延长对象寿命；对象销毁后调用闭包会悬空。[*this] 捕获对象副本，
  // 因而保留创建时状态，但要求对象可复制，且后续修改不会反映到副本。
}

TEST(Lambdas, ExplicitTemplateParametersConstrainGenericCallOperators) {
  auto add = []<typename Value>(Value left, Value right)
      requires std::is_arithmetic_v<Value>
  { return left + right; };

  static_assert(std::is_same_v<decltype(add(2, 3)), int>);
  static_assert(std::is_same_v<decltype(add(1.5, 2.5)), double>);
  EXPECT_EQ(add(2, 3), 5);
  EXPECT_DOUBLE_EQ(add(1.5, 2.5), 4.0);

  // C++20 lambda 可以显式写模板参数列表与 requires。两个参数都使用同一个 Value，
  // 因此 add(1, 2.5) 不会偷偷选公共类型，而是在模板实参推导阶段失败。
}

TEST(Lambdas, CapturelessClosureConvertsToAFunctionPointer) {
  auto twice = [](int value) { return value * 2; };
  int (*function)(int) = twice;

  EXPECT_EQ(function(6), 12);

  int offset = 3;
  auto capturing = [offset](int value) { return value + offset; };
  static_assert(!std::is_convertible_v<decltype(capturing), int (*)(int)>);

  // 无捕获闭包能转换成匹配的普通函数指针；有捕获闭包需要携带状态，没有可放进
  // 普通函数指针的对象地址，因此必须使用模板回调或其他类型擦除包装。
}

TEST(Lambdas, ConstexprAndRecursiveGenericLambdasWorkAtCompileTime) {
  constexpr auto square = [](int value) { return value * value; };
  static_assert(square(7) == 49);

  constexpr auto factorial = [](auto&& self, int value) -> int {
    return value < 2 ? 1 : value * self(self, value - 1);
  };
  static_assert(factorial(factorial, 5) == 120);
  EXPECT_EQ(factorial(factorial, 6), 720);

  // C++20 还没有显式对象参数，递归泛型 lambda 常把自身作为第一个参数传入。
  // 当函数体和参数满足常量表达式规则时，同一个闭包既可编译期求值也可运行期调用。
}

TEST(Lambdas, EachLambdaExpressionHasItsOwnUnnamedClosureType) {
  auto first = [] { return 1; };
  auto second = [] { return 1; };

  static_assert(!std::is_same_v<decltype(first), decltype(second)>);
  EXPECT_EQ(first(), second());

  // 即使源码和行为相同，每个 lambda-expression 仍产生唯一的未命名类类型。
  // 需要保存不同闭包时通常依赖模板、auto 或类型擦除，而不是猜测一个共同闭包类型。
}

}  // namespace
