// polyglot-covers:
// - cpp.language.function-declarations-and-return-types
// - cpp.language.value-reference-and-rvalue-reference-parameters
// - cpp.language.default-arguments
// - cpp.language.function-overload-resolution
// - cpp.language.overloaded-function-address
// - cpp.language.deleted-functions

// 跨语言迁移提示：C++ 的默认实参和重载选择发生在调用点的静态类型语境；Python
// 运行期执行签名绑定，JavaScript 则允许缺少或多出实参，三者的“同名调用”约束不同。

#include <gtest/gtest.h>

#include <string>
#include <type_traits>
#include <utility>

namespace {

int default_seed = 0;

int next_default() {
  ++default_seed;
  return default_seed;
}

int add_with_default(int value, int offset = next_default()) { return value + offset; }

void mutate_copy(int value) { value += 10; }
void mutate_reference(int& value) { value += 10; }
int observe_const_reference(const int& value) { return value; }

std::string reference_kind(const std::string&) { return "lvalue"; }
std::string reference_kind(std::string&&) { return "rvalue"; }

std::string numeric_kind(int) { return "int"; }
std::string numeric_kind(double) { return "double"; }
std::string numeric_kind(const char*) { return "pointer"; }

int combine(int left, int right) { return left + right; }
double combine(double left, double right) { return left + right; }

struct Token {
  explicit Token(int value) : value(value) {}
  int value;
};

void consume_token(Token) {}
void consume_token(double) = delete;

template <typename Value>
concept ConsumableToken = requires(Value value) { consume_token(value); };

TEST(Parameters, ValueReferenceAndConstReferenceExpressDifferentOwnership) {
  int number = 5;

  mutate_copy(number);
  EXPECT_EQ(number, 5);

  mutate_reference(number);
  EXPECT_EQ(number, 15);

  EXPECT_EQ(observe_const_reference(number), 15);
  EXPECT_EQ(observe_const_reference(20), 20);

  // 按值参数是调用者实参初始化出的独立对象；T& 表达可修改别名；const T& 既能绑定
  // 左值也能绑定临时量。接口应按所有权和修改语义选择，而不是只按“复制是否昂贵”。
}

TEST(Parameters, RvalueReferenceOverloadObservesTheArgumentCategory) {
  std::string text{"named"};

  EXPECT_EQ(reference_kind(text), "lvalue");
  EXPECT_EQ(reference_kind(std::move(text)), "rvalue");
  EXPECT_EQ(reference_kind(std::string{"temporary"}), "rvalue");

  // std::move 影响重载解析，但被调函数是否真正移动仍由其实现决定。本例只检查表达式
  // 类别；调用后不能因为选择了 T&& 重载就擅自假设源对象内容已经变化。
}

TEST(DefaultArguments, ExpressionsAreEvaluatedAtEachOmittedCall) {
  default_seed = 0;

  EXPECT_EQ(add_with_default(10), 11);
  EXPECT_EQ(add_with_default(10), 12);
  EXPECT_EQ(add_with_default(10, 40), 50);
  EXPECT_EQ(default_seed, 2);

  // 默认实参在调用点补入，并在每次省略实参的调用中求值；它不是函数定义时缓存的
  // 常量。默认实参也不属于函数类型，所以函数指针调用仍必须提供全部参数。
  using BinaryFunction = int (*)(int, int);
  BinaryFunction function = add_with_default;
  EXPECT_EQ(function(3, 4), 7);
}

TEST(OverloadResolution, ExactMatchBeatsPromotionAndConversion) {
  short small = 3;

  EXPECT_EQ(numeric_kind(3), "int");
  EXPECT_EQ(numeric_kind(3.5), "double");
  EXPECT_EQ(numeric_kind(small), "int");
  EXPECT_EQ(numeric_kind(nullptr), "pointer");

  // short 到 int 是 integral promotion，因此优于 short 到 double 的一般转换。
  // nullptr 只形成指针候选，不会像整数 0 那样首先精确匹配 int 重载。
}

TEST(OverloadResolution, TargetFunctionPointerTypeSelectsOneOverload) {
  using IntegerCombine = int (*)(int, int);
  using DoubleCombine = double (*)(double, double);

  IntegerCombine integers = combine;
  DoubleCombine doubles = combine;

  EXPECT_EQ(integers(2, 3), 5);
  EXPECT_DOUBLE_EQ(doubles(1.25, 2.5), 3.75);

  // 单独写 auto function = combine 没有足够上下文，重载集合不是一个可推导的值。
  // 目标函数指针类型为地址取得过程提供参数和返回类型，从而选择唯一重载。
}

TEST(DeletedFunctions, ADeletedBestMatchMakesTheCallIllFormed) {
  static_assert(ConsumableToken<Token>);
  static_assert(!ConsumableToken<double>);

  consume_token(Token{7});
  SUCCEED();

  // = delete 的函数仍参与重载解析；如果它是最佳匹配，调用在编译期失败，而不会退回
  // 较差的 Token 转换候选。删除重载适合阻止危险的隐式转换。
}

TEST(FunctionTypes, TopLevelConstOnAValueParameterIsNotPartOfTheSignature) {
  using Plain = void(int);
  using WrittenWithConst = void(const int);

  static_assert(std::is_same_v<Plain, WrittenWithConst>);

  // 对按值参数而言，函数内部是否把副本视为 const 不影响调用者，也不构成新重载。
  // 指针或引用指向对象的 const 则属于参数类型，会参与函数类型和重载解析。
}

}  // namespace
