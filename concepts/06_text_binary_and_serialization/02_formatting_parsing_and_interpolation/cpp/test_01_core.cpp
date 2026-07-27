// 格式化、解析与插值。
// 共同问题：插值何时求值；格式说明如何控制表示；解析是否接受前缀；
// 失败通过异常还是特殊值报告。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: formatting_parsing_and_interpolation
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_122_charconv_numeric_conversion_and_cxx20_formatting.cpp
// polyglot-related: languages/cpp/standard_library/14_input_output/
// polyglot-related+: test_130_formatted_output_manipulators_unformatted_write_and_custom_insertion.cpp

#include <gtest/gtest.h>

#include <charconv>
#include <iomanip>
#include <sstream>
#include <string>
#include <system_error>

namespace {

TEST(TextFormattingConcept, StreamFormattingUsesPersistentAndOneShotState) {
  std::ostringstream output;
  output << std::fixed << std::setprecision(2) << 12.345;

  EXPECT_EQ(output.str(), "12.35");
}

TEST(TextFormattingConcept, FromCharsParsesWithoutLocaleOrAllocation) {
  int value = 0;
  std::string text = "101";
  auto result = std::from_chars(text.data(), text.data() + text.size(), value, 2);

  EXPECT_EQ(result.ec, std::errc{});
  EXPECT_EQ(result.ptr, text.data() + text.size());
  EXPECT_EQ(value, 5);
}

TEST(TextFormattingConcept, FromCharsReportsWhereParsingStopped) {
  int value = 0;
  std::string text = "12px";
  auto result = std::from_chars(text.data(), text.data() + text.size(), value);

  EXPECT_EQ(result.ec, std::errc{});
  EXPECT_EQ(value, 12);
  EXPECT_EQ(*result.ptr, 'p');

  // Python int 严格要求完整字符串；JavaScript parseInt 也接受有效前缀。
}

TEST(TextFormattingConcept, InvalidPrefixUsesErrorCodeNotException) {
  int value = 0;
  std::string text = "value";
  auto result = std::from_chars(text.data(), text.data() + text.size(), value);

  EXPECT_EQ(result.ec, std::errc::invalid_argument);
}

}  // namespace
