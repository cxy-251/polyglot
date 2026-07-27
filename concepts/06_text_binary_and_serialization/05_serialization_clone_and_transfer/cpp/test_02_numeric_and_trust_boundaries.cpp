// 数值模型、类型恢复与信任边界。
// 共同问题：通用数据格式是否保留语言数值类型；非标准数值如何处理；
// 自定义反序列化如何限制可构造类型和字段。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/cpp/standard_library/13_strings_and_text/
// polyglot-related+: test_122_charconv_numeric_conversion_and_cxx20_formatting.cpp
// polyglot-related: languages/cpp/language/test_017_object_representation_alignment_and_bit_cast.cpp

#include <gtest/gtest.h>

#include <array>
#include <charconv>
#include <cstdint>
#include <span>
#include <stdexcept>
#include <string>

namespace {

std::int64_t decode_integer(const std::string& text) {
  std::int64_t value = 0;
  const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
  if (result.ec != std::errc{} || result.ptr != text.data() + text.size()) {
    throw std::invalid_argument{"invalid integer"};
  }
  return value;
}

struct Packet {
  std::int8_t value;
};

Packet decode_packet(std::span<const std::uint8_t> bytes) {
  constexpr std::uint8_t supported_version = 1;
  constexpr std::uint8_t point_tag = 1;
  if (bytes.size() != 3 ||
      bytes[0] != supported_version ||
      bytes[1] != point_tag) {
    throw std::invalid_argument{"unsupported packet"};
  }
  return Packet{static_cast<std::int8_t>(bytes[2])};
}

TEST(SerializationBoundaryConcept, ExplicitIntegerParserPreservesInt64Value) {
  const std::string text = "9007199254740993";

  EXPECT_EQ(decode_integer(text), INT64_C(9007199254740993));
  EXPECT_THROW(decode_integer("9007199254740993tail"), std::invalid_argument);

  // C++20 没有标准 JSON 类型；from_chars 按目标 int64_t 的范围精确解析，不会经过
  // JavaScript Number。协议仍须声明目标范围和溢出策略。
}

TEST(SerializationBoundaryConcept, DecoderWhitelistsLengthVersionAndTypeTag) {
  const std::array<std::uint8_t, 3> valid{1, 1, 0xF9};
  const std::array<std::uint8_t, 2> short_input{1, 1};
  const std::array<std::uint8_t, 4> trailing{1, 1, 7, 0};
  const std::array<std::uint8_t, 3> future_version{2, 1, 7};
  const std::array<std::uint8_t, 3> unknown_type{1, 9, 7};

  EXPECT_EQ(decode_packet(valid).value, -7);
  EXPECT_THROW(decode_packet(short_input), std::invalid_argument);
  EXPECT_THROW(decode_packet(trailing), std::invalid_argument);
  EXPECT_THROW(decode_packet(future_version), std::invalid_argument);
  EXPECT_THROW(decode_packet(unknown_type), std::invalid_argument);

  // 先验证完整边界再解释字段；不要按不可信标签构造任意类型，也不要直接持久化对象布局。
}

}  // namespace
