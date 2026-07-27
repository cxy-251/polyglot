// 规范化、非法编码与无损边界。
// 共同问题：规范等价文本是否自动相等；非法输入是拒绝、替换还是保留；
// 字符串模型能否直接表达孤立编码单元。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_117_character_traits_and_encoding_code_units.cpp
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_124_wide_multibyte_and_unicode_code_unit_conversions.cpp

#include <gtest/gtest.h>

#include <cstdint>
#include <string>
#include <string_view>

namespace {

bool is_valid_utf8(std::string_view text) {
  std::size_t index = 0;
  while (index < text.size()) {
    const auto lead = static_cast<std::uint8_t>(text[index]);
    if (lead <= 0x7F) {
      ++index;
      continue;
    }

    int continuation_count = 0;
    std::uint32_t code_point = 0;
    std::uint32_t minimum = 0;
    if (lead >= 0xC2 && lead <= 0xDF) {
      continuation_count = 1;
      code_point = lead & 0x1F;
      minimum = 0x80;
    } else if (lead >= 0xE0 && lead <= 0xEF) {
      continuation_count = 2;
      code_point = lead & 0x0F;
      minimum = 0x800;
    } else if (lead >= 0xF0 && lead <= 0xF4) {
      continuation_count = 3;
      code_point = lead & 0x07;
      minimum = 0x10000;
    } else {
      return false;
    }

    if (index + static_cast<std::size_t>(continuation_count) >= text.size()) {
      return false;
    }
    for (int offset = 1; offset <= continuation_count; ++offset) {
      const auto unit = static_cast<std::uint8_t>(text[index + offset]);
      if ((unit & 0xC0) != 0x80) {
        return false;
      }
      code_point = (code_point << 6) | (unit & 0x3F);
    }
    if (code_point < minimum ||
        (code_point >= 0xD800 && code_point <= 0xDFFF) ||
        code_point > 0x10FFFF) {
      return false;
    }
    index += static_cast<std::size_t>(continuation_count) + 1;
  }
  return true;
}

TEST(UnicodeBoundaryConcept, StandardStringsDoNotNormalizeEquivalentText) {
  const std::string composed = "\xC3\xA9";
  const std::string decomposed = "e\xCC\x81";

  EXPECT_NE(composed, decomposed);

  // C++20 标准库没有 Unicode normalization/grapheme API；应用必须选择并调用明确的
  // Unicode 库，不能把字节不等误判为用户可见文本必然不同。
}

TEST(UnicodeBoundaryConcept, ExplicitValidatorRejectsMalformedUtf8Classes) {
  EXPECT_TRUE(is_valid_utf8("A\xF0\x9F\x98\x80"));
  EXPECT_FALSE(is_valid_utf8(std::string{"\xF0\x9F", 2}));
  EXPECT_FALSE(is_valid_utf8(std::string{"\x80", 1}));
  EXPECT_FALSE(is_valid_utf8(std::string{"\xC0\xAF", 2}));
  EXPECT_FALSE(is_valid_utf8(std::string{"\xED\xA0\x80", 3}));
  EXPECT_FALSE(is_valid_utf8(std::string{"\xF4\x90\x80\x80", 4}));

  // std::string 仍可无损保存这些原始字节；validator 是应用协议边界，不是 string 构造
  // 或索引自动触发的机制。
}

}  // namespace
