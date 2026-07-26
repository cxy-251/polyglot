// Unicode 字符串、编码单元与用户可见字符。
// 共同问题：长度和索引按什么单位；编码何时变成字节；组合字符是否等于一个元素；
// 非法编码如何报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/cpp/language/test_013_literals_character_encodings_and_user_defined_literals.cpp

#include <gtest/gtest.h>

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
  static_assert(sizeof(char8_t) == 1);
  static_assert(sizeof(char16_t) == 2);
  static_assert(sizeof(char32_t) == 4);
  static_assert(!std::is_same_v<char, char8_t>);
}

}  // namespace
