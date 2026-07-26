// polyglot-covers:
// - cpp.language.integer-and-floating-literals
// - cpp.language.character-and-string-literal-types
// - cpp.language.escape-raw-and-concatenated-strings
// - cpp.language.embedded-null-characters
// - cpp.language.user-defined-literals

// 跨语言迁移提示：C++ 字符串字面量的元素类型与源/执行字符集相关，只保存 code unit；
// Python str 按 code point 建模，JavaScript 字符串按 UTF-16 code unit 索引，长度含义并不相同。

#include <gtest/gtest.h>

#include <cstddef>
#include <string>
#include <string_view>
#include <type_traits>

namespace {

struct Kilometres {
  unsigned long long value;
};

consteval Kilometres operator""_km(unsigned long long value) {
  return Kilometres{value};
}

TEST(IntegerLiterals, BasePrefixesSeparatorsAndSuffixesAffectTheToken) {
  int decimal = 42;
  int octal = 052;
  int hexadecimal = 0x2A;
  int binary = 0b0010'1010;

  EXPECT_EQ(decimal, 42);
  EXPECT_EQ(octal, 42);
  EXPECT_EQ(hexadecimal, 42);
  EXPECT_EQ(binary, 42);

  auto unsigned_long_long = 42ULL;
  static_assert(std::is_same_v<decltype(unsigned_long_long), unsigned long long>);

  // 前导 0 表示八进制，而不是普通的十进制补零；09 甚至不是合法八进制 token。
  // 单引号数字分隔符不改变值。u、l、ll 后缀则改变候选类型集合。
}

TEST(IntegerLiterals, UnsuffixedDecimalChoosesTheFirstRepresentableSignedType) {
  auto large_decimal = 2'147'483'648;

  static_assert(std::is_integral_v<decltype(large_decimal)>);
  static_assert(std::is_signed_v<decltype(large_decimal)>);
  EXPECT_GE(sizeof(large_decimal), 4U);
  EXPECT_EQ(large_decimal, 2'147'483'648LL);

  // 无后缀十进制依次尝试 int、long、long long；具体选 long 还是 long long 取决于平台。
  // 十六进制和八进制的候选列表还会穿插 unsigned 类型，不能只凭数值大小猜 signedness。
}

TEST(FloatingLiterals, ExponentAndHexadecimalFormsRepresentTheSameValue) {
  double decimal = 12.5;
  double scientific = 1.25e1;
  double hexadecimal = 0x1.9p3;
  float single_precision = 12.5F;

  EXPECT_DOUBLE_EQ(decimal, scientific);
  EXPECT_DOUBLE_EQ(decimal, hexadecimal);
  EXPECT_FLOAT_EQ(single_precision, 12.5F);

  // 十六进制浮点的 p 指数以 2 为底：0x1.9 等于 1 + 9/16，乘 2^3 得到 12.5。
  // 无后缀浮点字面量是 double；f 和 l 分别请求 float 与 long double。
}

TEST(CharacterLiterals, PrefixSelectsTheCodeUnitType) {
  static_assert(std::is_same_v<decltype('A'), char>);
  static_assert(std::is_same_v<decltype(u8'A'), char8_t>);
  static_assert(std::is_same_v<decltype(u'A'), char16_t>);
  static_assert(std::is_same_v<decltype(U'A'), char32_t>);
  static_assert(std::is_same_v<decltype(L'A'), wchar_t>);

  EXPECT_EQ('\x41', 'A');
  EXPECT_EQ('\101', 'A');

  // 普通字符字面量在 C++ 中是 char。多字符字面量如 'ab' 具有实现定义值，既不适合
  // 表示两个字符也不便移植；文本编码应选择明确的代码单元类型和字符串设施。
}

TEST(StringLiterals, ArrayTypeIncludesTheTrailingNullCodeUnit) {
  using Narrow = std::remove_reference_t<decltype("hi")>;
  using Utf8 = std::remove_reference_t<decltype(u8"hi")>;

  static_assert(std::is_same_v<Narrow, const char[3]>);
  static_assert(std::is_same_v<Utf8, const char8_t[3]>);

  constexpr char text[] = "hi";
  EXPECT_EQ(sizeof(text), 3U);
  EXPECT_EQ(text[2], '\0');

  // 字符串字面量是 const 数组，不是 std::string。多数表达式会让它退化成指针，
  // 因而丢失编译期长度；用数组引用或 string_view 可以保留长度信息。
}

TEST(StringLiterals, RawAndAdjacentLiteralsAvoidRuntimeConcatenation) {
  std::string raw = R"json({"path":"C:\\tmp","lines":"a\nb"})json";
  std::string adjacent = "compile " "time " "concatenation";

  EXPECT_EQ(raw, R"({"path":"C:\\tmp","lines":"a\nb"})");
  EXPECT_EQ(adjacent, "compile time concatenation");

  // raw string 不解释反斜杠转义，自定义 delimiter 允许正文包含普通 )" 片段。
  // 相邻兼容字符串 token 在翻译阶段拼接，不产生运行期 operator+ 或临时 string。
}

TEST(StringLiterals, EmbeddedNullRequiresAnExplicitLengthAwareView) {
  constexpr char bytes[] = "ab\0cd";
  std::string_view complete{bytes, sizeof(bytes) - 1};
  std::string_view truncated{bytes};

  EXPECT_EQ(complete.size(), 5U);
  EXPECT_EQ(complete.substr(3), "cd");
  EXPECT_EQ(truncated.size(), 2U);

  // 数组可以在结尾零字符前包含额外的 '\0'。只接收 const char* 的 C 接口通常在
  // 第一个零处停止；需要二进制或含零文本时必须同时传递长度。
}

TEST(UserDefinedLiterals, AReservedSuffixBuildsADomainValueAtCompileTime) {
  constexpr Kilometres distance = 12_km;
  static_assert(distance.value == 12);
  EXPECT_EQ(distance.value, 12U);

  // 用户定义后缀必须以下划线开头，避免与标准将来加入的后缀冲突。整数 raw form
  // 可以接收 unsigned long long；consteval 让构造和校验必须在编译期完成。
}

}  // namespace
