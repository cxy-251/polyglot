// 数值模型与转换。
// 共同问题：整数是否溢出；浮点特殊值如何表现；显式转换如何报告失败；
// 混合运算采用什么结果类型。
//
// polyglot-family: values_and_comparison
// polyglot-concept: numeric_models_and_conversion
// polyglot-related: languages/cpp/language/test_001_fundamental_types_objects_and_initialization.cpp
// polyglot-related: languages/cpp/language/test_003_expression_value_categories_and_conversions.cpp

#include <gtest/gtest.h>

#include <charconv>
#include <cmath>
#include <cstdint>
#include <limits>
#include <string_view>
#include <system_error>
#include <type_traits>

namespace {

TEST(NumericModelsConcept, IntegerWidthAndOverflowRulesArePartOfTheType) {
  static_assert(std::numeric_limits<std::uint32_t>::digits == 32);
  std::uint32_t maximum = std::numeric_limits<std::uint32_t>::max();

  EXPECT_EQ(maximum + std::uint32_t{1}, std::uint32_t{0});

  // 无符号整数按 2^N 取模；有符号溢出是未定义行为，不能像 Python 大整数那样继续增长，
  // 也不能通过执行溢出来证明这个规则。
}

TEST(NumericModelsConcept, FloatingPointExposesIeeeSpecialValues) {
  double nan = std::numeric_limits<double>::quiet_NaN();
  double infinity = std::numeric_limits<double>::infinity();

  EXPECT_TRUE(std::isnan(nan));
  EXPECT_FALSE(nan == nan);
  EXPECT_TRUE(std::isinf(infinity));
  EXPECT_TRUE(std::signbit(-0.0));
}

TEST(NumericModelsConcept, ExplicitConversionCanTruncateOrReportParseFailure) {
  EXPECT_EQ(static_cast<int>(3.9), 3);

  int parsed = 0;
  std::string_view valid = "42";
  auto success = std::from_chars(valid.data(), valid.data() + valid.size(), parsed);
  EXPECT_EQ(success.ec, std::errc{});
  EXPECT_EQ(parsed, 42);

  std::string_view invalid = "value";
  auto failure = std::from_chars(invalid.data(), invalid.data() + invalid.size(), parsed);
  EXPECT_EQ(failure.ec, std::errc::invalid_argument);
}

TEST(NumericModelsConcept, UsualArithmeticConversionsAndDivisionUseStaticTypes) {
  static_assert(std::is_same_v<decltype(3 + 0.5), double>);
  static_assert(std::is_same_v<decltype(7 / 2), int>);

  EXPECT_DOUBLE_EQ(3 + 0.5, 3.5);
  EXPECT_EQ(7 / 2, 3);
  EXPECT_EQ(-7 / 2, -3);
  EXPECT_EQ(-7 % 2, -1);
}

}  // namespace

