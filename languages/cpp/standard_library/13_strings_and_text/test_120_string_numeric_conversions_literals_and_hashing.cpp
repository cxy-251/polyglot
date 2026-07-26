// polyglot-covers:
// - cpp.stdlib.strings.sto-integer-base-position-and-prefix
// - cpp.stdlib.strings.sto-partial-parse-errors-and-range
// - cpp.stdlib.strings.unsigned-conversion-leading-minus
// - cpp.stdlib.strings.sto-floating-special-values-and-suffix
// - cpp.stdlib.strings.to-string-and-to-wstring-cxx20-format
// - cpp.stdlib.strings.string-literals-and-embedded-null
// - cpp.stdlib.strings.basic-string-hash-contract

#include <gtest/gtest.h>

#include <cmath>
#include <cstddef>
#include <functional>
#include <limits>
#include <string>
#include <type_traits>

namespace {

TEST(StringIntegerConversions, BaseZeroRecognizesPrefixesAndReportsTheStoppingPosition) {
  std::size_t parsed = 0;
  const int value = std::stoi("  -0x2a rest", &parsed, 0);

  EXPECT_EQ(value, -42);
  EXPECT_EQ(parsed, 7U);
  EXPECT_EQ(std::stoi("077", nullptr, 0), 63);
  EXPECT_EQ(std::stoi("101", nullptr, 2), 5);
  EXPECT_EQ(std::stoll("7fffffff", nullptr, 16), 2'147'483'647LL);

  // base=0 沿用 C 数字前缀规则：0x 是十六进制，前导 0 是八进制；它并不总是
  // 用户输入想要的十进制。pos 是原字符串中首个未转换字符的位置，包括前导空白。
}

TEST(StringIntegerConversions, SuccessfulPrefixDoesNotRequireTheWholeStringToBeNumeric) {
  std::size_t parsed = 0;
  const int value = std::stoi("42xyz", &parsed);

  EXPECT_EQ(value, 42);
  EXPECT_EQ(parsed, 2U);
  EXPECT_THROW(std::stoi("words"), std::invalid_argument);
  EXPECT_THROW(std::stoi("999999999999999999999999"), std::out_of_range);

  // stoi 系列接受“最长可转换前缀”；需要严格校验整个字段时还必须检查 pos==size。
  // 没有任何转换抛 invalid_argument，数学结果目标类型放不下则抛 out_of_range。
}

TEST(StringUnsignedConversions, ALeadingMinusIsAcceptedThenNegatedInTheUnsignedType) {
  const auto value = std::stoul("-1");

  EXPECT_EQ(value, std::numeric_limits<unsigned long>::max());

  // stoul 不是“拒绝负号”的验证器：语法允许负号，然后在无符号结果类型中取负。
  // 接收业务上的非负数时，应先验证语法或使用 from_chars 后额外检查符号策略。
}

TEST(StringFloatingConversions, TheyAcceptSpecialValuesAndStopAtAnUnparsedSuffix) {
  std::size_t parsed = 0;
  const double value = std::stod("  1.25e2ms", &parsed);

  EXPECT_DOUBLE_EQ(value, 125.0);
  EXPECT_EQ(parsed, 8U);
  EXPECT_TRUE(std::isinf(std::stod("INF")));
  EXPECT_TRUE(std::isnan(std::stod("NAN")));
  EXPECT_THROW(std::stod("."), std::invalid_argument);

  // 浮点转换依赖对应的 C 库规则并受当前 C locale 影响；INF、NAN 也可能是合法输入。
  // 对协议字段要同时固定 locale、允许的特殊值以及是否容许单位等尾缀。
}

TEST(StringOutputConversions, Cxx20ToStringUsesThePrintfStyleDecimalRepresentation) {
  EXPECT_EQ(std::to_string(42), "42");
  EXPECT_EQ(std::to_string(3.5), "3.500000");
  EXPECT_EQ(std::to_wstring(-7), L"-7");
  EXPECT_EQ(std::to_string('A'), std::to_string(static_cast<int>('A')));

  // C++20 的浮点 to_string 等价于 printf 风格的固定小数输出，常带无意义尾零，
  // 且 char 会整型提升为编码数值。精确控制格式应使用 charconv、format 或流。
}

TEST(StringLiterals, SuffixConstructsOwningStringsAndPreservesEmbeddedNulls) {
  using namespace std::string_literals;

  const auto narrow = "A\0B"s;
  const auto utf8 = u8"猫"s;
  const auto utf16 = u"猫"s;
  const auto wide = L"wide"s;

  static_assert(std::is_same_v<decltype("x"s), std::string>);
  static_assert(std::is_same_v<decltype(u8"x"s), std::u8string>);
  static_assert(std::is_same_v<decltype(u"x"s), std::u16string>);
  static_assert(std::is_same_v<decltype(U"x"s), std::u32string>);
  static_assert(std::is_same_v<decltype(L"x"s), std::wstring>);

  EXPECT_EQ(narrow.size(), 3U);
  EXPECT_EQ(narrow[1], '\0');
  EXPECT_EQ(utf8.size(), 3U);
  EXPECT_EQ(utf16.size(), 1U);
  EXPECT_EQ(wide.size(), 4U);

  // s 后缀按字面量的编译期长度构造拥有型字符串，因此不会在内嵌零处截断。
  // 不同前缀产生不同代码单元类型；它们之间没有自动的 Unicode 转码。
}

TEST(StringHashing, EqualStringsHaveEqualHashesButValuesAreNotPersistenceFormats) {
  const std::string first{"same"};
  const std::string second{"same"};
  const std::string different{"Same"};
  const std::hash<std::string> hash;

  EXPECT_EQ(hash(first), hash(second));
  EXPECT_EQ(std::equal_to<std::string>{}(first, second), hash(first) == hash(second));
  EXPECT_NE(first, different);

  // 标准只要求相等键在一次程序执行中得到相等散列；不同键可以碰撞，具体数值也
  // 不保证跨平台、标准库版本或进程稳定，不能写入文件充当持久 ID。
}

}  // namespace
