// Unicode 字符串、编码单元与用户可见字符。
// 共同问题：长度和索引按什么单位；编码何时变成字节；组合字符是否等于一个元素；
// 非法编码如何报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_117_character_traits_and_encoding_code_units.cpp
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_124_wide_multibyte_and_unicode_code_unit_conversions.cpp

#include <gtest/gtest.h>

#include <climits>
#include <limits>
#include <string>
#include <type_traits>

namespace {

TEST(UnicodeStringsConcept, StringSizeCountsCodeUnitsOfItsElementType) {
  std::string utf8 = "A\xF0\x9F\x98\x80";
  std::u16string utf16 = u"A😀";
  std::u32string utf32 = U"A😀";

  EXPECT_EQ(utf8.size(), 5U);
  EXPECT_EQ(utf16.size(), 3U);
  EXPECT_EQ(utf32.size(), 2U);
}

TEST(UnicodeStringsConcept, IndexReturnsOneCodeUnitNotOneGrapheme) {
  std::u16string text = u"😀";

  EXPECT_EQ(text.size(), 2U);
  EXPECT_NE(text[0], text[1]);
}

TEST(UnicodeStringsConcept, StringDoesNotDeclareOrValidateAnEncoding) {
  std::string invalid{"\xFF", 1};

  EXPECT_EQ(invalid.size(), 1U);
  EXPECT_EQ(static_cast<unsigned char>(invalid[0]), 0xFF);

  // std::string 只是 char 序列；UTF-8 校验、规范化和 grapheme 分段需要额外设施。
}

TEST(UnicodeStringsConcept, CharacterTypesRepresentDifferentCodeUnitWidths) {
  static_assert(!std::is_same_v<char, char8_t>);
  static_assert(!std::is_same_v<char8_t, char16_t>);
  static_assert(!std::is_same_v<char16_t, char32_t>);
  static_assert(std::numeric_limits<char16_t>::digits >= 16);
  static_assert(std::numeric_limits<char32_t>::digits >= 32);

  EXPECT_GE(sizeof(char16_t) * CHAR_BIT, std::numeric_limits<char16_t>::digits);
  EXPECT_GE(sizeof(char32_t) * CHAR_BIT, std::numeric_limits<char32_t>::digits);

  // char16_t/char32_t 分别能保存 UTF-16/UTF-32 code unit，这是类型语义；上面的
  // sizeof * CHAR_BIT 只是锁定 ABI 的存储观察。sizeof 的单位是 byte，语言不普遍保证
  // 一个 byte 恰好为 8 bit。
}

}  // namespace
