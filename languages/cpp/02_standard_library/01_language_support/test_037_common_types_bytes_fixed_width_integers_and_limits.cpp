// polyglot-covers:
// - cpp.stdlib.language-support.size-t-and-ptrdiff-t
// - cpp.stdlib.language-support.nullptr-t-and-max-align-t
// - cpp.stdlib.language-support.byte
// - cpp.stdlib.language-support.offsetof
// - cpp.stdlib.language-support.fixed-width-integer-types
// - cpp.stdlib.language-support.numeric-limits
// - cpp.stdlib.language-support.floating-point-special-values

#include <gtest/gtest.h>

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <type_traits>

namespace {

struct StandardLayoutRecord {
  char tag;
  std::uint32_t payload;
};

TEST(CommonTypes, SizeAndPointerDifferenceRepresentDifferentDomains) {
  std::array<int, 4> values{2, 3, 5, 7};
  const std::size_t count = values.size();
  const std::ptrdiff_t distance = values.end() - values.begin();

  EXPECT_EQ(count, 4U);
  EXPECT_EQ(distance, 4);
  static_assert(std::is_unsigned_v<std::size_t>);
  static_assert(std::is_signed_v<std::ptrdiff_t>);

  // size_t 表示对象大小和容器容量，不能表达负差；ptrdiff_t 表示同一数组内的指针差。
  // 把负 distance 直接转换为 size_t 会得到很大的无符号值，应先检查范围和符号。
}

TEST(CommonTypes, NullptrTypeConvertsToPointersButNotOrdinaryIntegers) {
  static_assert(std::is_same_v<decltype(nullptr), std::nullptr_t>);
  static_assert(std::is_convertible_v<std::nullptr_t, int*>);
  static_assert(!std::is_convertible_v<std::nullptr_t, int>);

  int* pointer = nullptr;
  EXPECT_EQ(pointer, nullptr);

  // nullptr_t 使空指针进入指针重载，而不会像字面量 0 那样同时成为整数候选。
  // 它仍不携带目标指针类型，赋值或调用上下文负责完成具体指针转换。
}

TEST(Bytes, ByteSupportsBitManipulationWithoutPretendingToBeANumber) {
  std::byte flags{0b0001'0010};
  flags |= std::byte{0b1000'0000};
  const std::byte low_nibble = flags & std::byte{0b0000'1111};

  EXPECT_EQ(std::to_integer<unsigned int>(flags), 0b1001'0010U);
  EXPECT_EQ(std::to_integer<unsigned int>(low_nibble), 0b0010U);
  static_assert(!std::is_arithmetic_v<std::byte>);

  // byte 表示原始存储单位并提供位运算，但没有整数加减和隐式数值转换。协议字段需要
  // 数值含义时应显式 to_integer，避免把内存字节意外当成字符或小整数参与算术。
}

TEST(ObjectLayout, OffsetofIsForStandardLayoutTypes) {
  static_assert(std::is_standard_layout_v<StandardLayoutRecord>);
  constexpr std::size_t tag_offset = offsetof(StandardLayoutRecord, tag);
  constexpr std::size_t payload_offset = offsetof(StandardLayoutRecord, payload);

  EXPECT_EQ(tag_offset, 0U);
  EXPECT_GE(payload_offset, sizeof(char));
  EXPECT_LT(payload_offset, sizeof(StandardLayoutRecord));

  // padding 的准确数量由 ABI 决定，不能断言 payload 紧跟 char。offsetof 只保证可用于
  // standard-layout 类型；对复杂继承或虚函数类型使用属于条件支持或不可移植做法。
}

TEST(FixedWidthIntegers, ExactLeastAndFastFamiliesExpressDifferentPromises) {
  static_assert(sizeof(std::int8_t) * std::numeric_limits<unsigned char>::digits == 8);
  static_assert(sizeof(std::int32_t) * std::numeric_limits<unsigned char>::digits == 32);
  static_assert(std::numeric_limits<std::int_least16_t>::digits >= 15);
  static_assert(std::numeric_limits<std::uint_fast32_t>::digits >= 32);

  std::int32_t signed_value = INT32_C(-2'000'000);
  std::uint64_t unsigned_value = UINT64_C(9'000'000'000);
  EXPECT_LT(signed_value, 0);
  EXPECT_EQ(unsigned_value, 9'000'000'000ULL);

  // intN_t 只在实现有恰好 N 位且无 padding 的整数类型时提供；本仓库基线具备常见宽度。
  // least 保证至少该宽度，fast 倾向速度；序列化格式应选明确协议宽度而非 fast 类型。
}

TEST(NumericLimits, MinAndLowestMeanDifferentThingsForFloatingPoint) {
  constexpr double minimum_positive = std::numeric_limits<double>::min();
  constexpr double lowest = std::numeric_limits<double>::lowest();
  constexpr double maximum = std::numeric_limits<double>::max();

  EXPECT_GT(minimum_positive, 0.0);
  EXPECT_LT(lowest, 0.0);
  EXPECT_EQ(lowest, -maximum);

  // 浮点 min() 是最小正规正数，不是最负值；泛型代码要找下界应使用 lowest()。
  // 对整数，min() 与 lowest() 相同，这个差异很容易在模板初始化哨兵时被忽略。
}

TEST(NumericLimits, InfinityNanAndEpsilonNeedPurposeSpecificChecks) {
  const double infinity = std::numeric_limits<double>::infinity();
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const double epsilon = std::numeric_limits<double>::epsilon();

  EXPECT_TRUE(std::numeric_limits<double>::has_infinity);
  EXPECT_TRUE(std::isinf(infinity));
  EXPECT_TRUE(std::isnan(nan));
  EXPECT_NE(nan, nan);
  EXPECT_GT(1.0 + epsilon, 1.0);

  // epsilon 是 1 附近相邻可表示值的间距，不是适合所有量级的通用误差阈值。NaN 与任何
  // 值（包括自身）的相等比较都为 false，应使用 isnan；无穷值则用 isinf。
}

TEST(CommonTypes, MaxAlignTProvidesOnlyTheFundamentalAlignmentBaseline) {
  EXPECT_GE(alignof(std::max_align_t), alignof(double));

  struct alignas(64) OverAligned {
    char value;
  };
  static_assert(alignof(OverAligned) == 64);

  // max_align_t 覆盖实现支持的 fundamental alignment，不保证满足显式 over-aligned 类型。
  // 为后者取得动态存储时要使用支持 align_val_t 的分配接口或能感知 alignment 的 allocator。
}

}  // namespace
