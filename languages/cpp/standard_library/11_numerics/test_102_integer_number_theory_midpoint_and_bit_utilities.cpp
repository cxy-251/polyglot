// polyglot-covers:
// - cpp.stdlib.numeric.gcd-sign-zero-common-type-and-representability
// - cpp.stdlib.numeric.lcm-sign-zero-and-overflow-precondition
// - cpp.stdlib.numeric.midpoint-integer-overflow-and-rounding-toward-first
// - cpp.stdlib.numeric.midpoint-floating-point-and-pointer-overloads
// - cpp.stdlib.bit.unsigned-type-constraints
// - cpp.stdlib.bit.has-single-bit-and-power-of-two-boundaries
// - cpp.stdlib.bit.bit-ceil-floor-width
// - cpp.stdlib.bit.rotl-rotr-modular-and-negative-counts
// - cpp.stdlib.bit.leading-trailing-bit-count-and-popcount
// - cpp.stdlib.bit.endian-native-and-mixed-representation
// - cpp.stdlib.bit.constexpr-noexcept-integer-utilities

#include <gtest/gtest.h>

#include <array>
#include <bit>
#include <cstdint>
#include <limits>
#include <numeric>
#include <type_traits>

namespace {

TEST(Gcd, ItUsesAbsoluteValuesAndDefinesTheDoubleZeroCase) {
  EXPECT_EQ(std::gcd(48, 18), 6);
  EXPECT_EQ(std::gcd(-48, 18), 6);
  EXPECT_EQ(std::gcd(48, -18), 6);
  EXPECT_EQ(std::gcd(0, 9), 9);
  EXPECT_EQ(std::gcd(0, 0), 0);

  // gcd 返回 |m|、|n| 的最大公约数；两者都为零时特意定义为零。bool 不属于允许的
  // integer 类型。
}

TEST(Gcd, MixedIntegerTypesReturnTheirCommonType) {
  const short left = 84;
  const long long right = 30;
  const auto result = std::gcd(left, right);

  static_assert(std::is_same_v<decltype(result), const long long>);
  EXPECT_EQ(result, 6);

  // 返回 common_type_t<M,N>。前置条件还要求两个绝对值都能由该共同类型表示；例如对
  // 最小有符号值盲目取绝对值可能不可表示，不能拿它测试“实现如何溢出”。
}

TEST(Lcm, ItUsesAbsoluteValuesAndAnyZeroMakesTheResultZero) {
  EXPECT_EQ(std::lcm(12, 18), 36);
  EXPECT_EQ(std::lcm(-12, 18), 36);
  EXPECT_EQ(std::lcm(0, 18), 0);
  EXPECT_EQ(std::lcm(18, 0), 0);

  // 非零结果要求 lcm 可由共同类型表示；接口不承诺用饱和值或异常报告乘法溢出，调用
  // 前必须限制输入范围或使用更宽类型。
}

TEST(GcdLcm, ProductIdentityHoldsWhenTheValuesAreRepresentable) {
  constexpr int left = 21;
  constexpr int right = 6;

  static_assert(std::gcd(left, right) == 3);
  static_assert(std::lcm(left, right) == 42);
  EXPECT_EQ(std::gcd(left, right) * std::lcm(left, right), left * right);

  // 对非零且中间结果可表示的整数，gcd*lcm == |m*n|；这不是绕过 lcm 可表示前置条件
  // 的溢出检测技巧。
}

TEST(Midpoint, IntegerOddDistanceRoundsTowardTheFirstArgument) {
  EXPECT_EQ(std::midpoint(0, 5), 2);
  EXPECT_EQ(std::midpoint(5, 0), 3);
  EXPECT_EQ(std::midpoint(-5, 0), -3);
  EXPECT_EQ(std::midpoint(0, -5), -2);

  // 和为奇数时结果向第一个实参 a 舍入，所以交换参数可能相差 1；midpoint 不是无条件
  // 对称的整数函数。
}

TEST(Midpoint, IntegerImplementationAvoidsOverflowOfTheMathematicalSum) {
  constexpr int minimum = std::numeric_limits<int>::min();
  constexpr int maximum = std::numeric_limits<int>::max();

  EXPECT_EQ(std::midpoint(maximum, minimum), 0);
  EXPECT_EQ(std::midpoint(minimum, maximum), -1);
  EXPECT_EQ(std::midpoint(maximum - 2, maximum), maximum - 1);

  // 直接写 `(a+b)/2` 可能有有符号溢出；std::midpoint 保证不发生该溢出，并保留向 a
  // 舍入的语义。
}

TEST(Midpoint, FloatingPointUsesAtMostOneInexactOperation) {
  const double maximum = std::numeric_limits<double>::max();

  EXPECT_EQ(std::midpoint(maximum, maximum), maximum);
  EXPECT_DOUBLE_EQ(std::midpoint(maximum, -maximum), 0.0);

  // 简单 `(a+b)/2` 的同号大数加法可先溢出为无穷；midpoint 选择安全计算路径。浮点
  // 结果仍受舍入模式和可表示精度约束。
}

TEST(Midpoint, PointerOverloadStaysWithinOneArrayAndRoundsTowardTheFirst) {
  std::array<int, 6> values{0, 1, 2, 3, 4, 5};
  int* first = values.data();
  int* sixth = values.data() + 5;
  int* end = values.data() + values.size();

  EXPECT_EQ(std::midpoint(first, end), values.data() + 3);
  EXPECT_EQ(std::midpoint(first, sixth), values.data() + 2);
  EXPECT_EQ(std::midpoint(sixth, first), values.data() + 3);

  // 两指针必须指向同一数组对象（允许 past-the-end）；无关对象指针没有合法距离，不能
  // 传给 midpoint。奇数距离同样向第一个指针舍入。
}

template <class T>
concept HasSingleBitCallable = requires(T value) {
  std::has_single_bit(value);
};

template <class T>
concept PopcountCallable = requires(T value) {
  std::popcount(value);
};

TEST(BitConstraints, PowerAndCountFunctionsAcceptUnsignedIntegerTypesOnly) {
  static_assert(HasSingleBitCallable<unsigned>);
  static_assert(HasSingleBitCallable<std::uint8_t>);
  static_assert(!HasSingleBitCallable<int>);
  static_assert(!HasSingleBitCallable<bool>);
  static_assert(PopcountCallable<unsigned long long>);
  static_assert(!PopcountCallable<long long>);


  // 使用 unsigned 让移位、旋转和位宽具有明确模数与位数；不能把 signed 负数的表示细节
  // 直接交给这些受约束模板。
}

TEST(PowersOfTwo, SingleBitCeilFloorAndWidthHaveDifferentBoundaryQuestions) {
  EXPECT_FALSE(std::has_single_bit(0U));
  EXPECT_TRUE(std::has_single_bit(1U));
  EXPECT_TRUE(std::has_single_bit(8U));
  EXPECT_FALSE(std::has_single_bit(10U));

  EXPECT_EQ(std::bit_ceil(0U), 1U);
  EXPECT_EQ(std::bit_ceil(1U), 1U);
  EXPECT_EQ(std::bit_ceil(9U), 16U);
  EXPECT_EQ(std::bit_floor(0U), 0U);
  EXPECT_EQ(std::bit_floor(9U), 8U);
  EXPECT_EQ(std::bit_width(0U), 0U);
  EXPECT_EQ(std::bit_width(9U), 4U);

  // bit_ceil 找不小于 x 的最小 2 次幂，0/1 都返回 1；bit_floor(0) 返回 0；bit_width
  // 是表示 x 所需的有效位数。bit_ceil 的目标值必须能由 T 表示。
}

TEST(BitRotation, CountsAreReducedModuloWidthAndNegativeCountsReverseDirection) {
  constexpr std::uint8_t value = 0b1000'0001U;

  EXPECT_EQ(std::rotl(value, 1), static_cast<std::uint8_t>(0b0000'0011U));
  EXPECT_EQ(std::rotr(value, 1), static_cast<std::uint8_t>(0b1100'0000U));
  EXPECT_EQ(std::rotl(value, 9), std::rotl(value, 1));
  EXPECT_EQ(std::rotl(value, -1), std::rotr(value, 1));
  EXPECT_EQ(std::rotr(value, -1), std::rotl(value, 1));

  // s 先对 numeric_limits<T>::digits 取模；负余数把方向交给另一个旋转函数。和普通
  // shift 不同，被移出的一端会回卷，不会丢弃。
}

TEST(BitCounting, LeadingTrailingAndPopulationCountsInspectDifferentPatterns) {
  constexpr std::uint8_t value = 0b0001'1000U;
  constexpr std::uint8_t leading_ones = 0b1110'0000U;
  constexpr std::uint8_t trailing_ones = 0b0001'1111U;

  EXPECT_EQ(std::countl_zero(value), 3);
  EXPECT_EQ(std::countr_zero(value), 3);
  EXPECT_EQ(std::countl_one(leading_ones), 3);
  EXPECT_EQ(std::countr_one(trailing_ones), 5);
  EXPECT_EQ(std::popcount(value), 2);

  // leading 从最高有效位开始，trailing 从最低位开始，popcount 统计全体 1。
}

TEST(BitCounting, ZeroAndAllOnesReturnTheFullUnsignedWidth) {
  constexpr auto digits = std::numeric_limits<std::uint16_t>::digits;
  constexpr auto all_ones = std::numeric_limits<std::uint16_t>::max();

  EXPECT_EQ(std::countl_zero(std::uint16_t{0}), digits);
  EXPECT_EQ(std::countr_zero(std::uint16_t{0}), digits);
  EXPECT_EQ(std::countl_one(all_ones), digits);
  EXPECT_EQ(std::countr_one(all_ones), digits);
  EXPECT_EQ(std::popcount(all_ones), digits);
}

TEST(Endian, NativeMayBeLittleBigOrAPlatformSpecificMixedOrder) {
  if constexpr (std::endian::little == std::endian::big) {
    // 标准为“所有标量类型大小均为 1”的实现保留了 little == big 的可能性。
    EXPECT_EQ(std::endian::native, std::endian::little);
  } else if constexpr (std::endian::native == std::endian::little) {
    EXPECT_EQ(std::endian::native, std::endian::little);
  } else if constexpr (std::endian::native == std::endian::big) {
    EXPECT_EQ(std::endian::native, std::endian::big);
  } else {
    EXPECT_NE(std::endian::native, std::endian::little);
    EXPECT_NE(std::endian::native, std::endian::big);
  }

  // 测试不锁定当前容器为 little-endian；native 也允许混合序。网络/文件协议应明确编码
  // 字节顺序，不能把对象表示直接写出并假设其他主机相同。std::byteswap 是 C++23。
}

constexpr bool IntegerUtilitiesWorkAtCompileTime() {
  return std::gcd(18, 12) == 6 &&
         std::midpoint(1, 4) == 2 &&
         std::bit_floor(31U) == 16U &&
         std::popcount(0b1011U) == 3;
}

static_assert(IntegerUtilitiesWorkAtCompileTime());
static_assert(noexcept(std::midpoint(1, 4)));
static_assert(noexcept(std::rotl(1U, 3)));

TEST(IntegerUtilities, ConstexprAndNoexceptRemainSeparateQuestions) {
  EXPECT_TRUE(IntegerUtilitiesWorkAtCompileTime());

  // gcd 的效果条款写明 Throws: Nothing，但标准展示的声明本身没有 noexcept；实现可
  // 加强异常说明，因而本项目的 libstdc++ 11 和宿主 libc++ 得到的 noexcept 表达式值
  // 不同。midpoint 的算术重载和 rotl 则由标准显式声明 noexcept。常量求值能力、行为
  // 上不抛异常和函数类型的异常说明是三个相关但不能混为一谈的问题。
#if defined(__GLIBCXX__)
  EXPECT_TRUE(noexcept(std::gcd(18, 12)));
#else
#endif
}

}  // namespace
