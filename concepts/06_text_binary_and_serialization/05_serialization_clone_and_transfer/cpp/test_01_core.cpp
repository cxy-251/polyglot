// 序列化、克隆与所有权转移。
// 共同问题：哪些值可以跨边界编码；对象图复制是否保留别名和循环；
// 自定义类型如何参与；反序列化是否安全。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/cpp/language/test_008_classes_construction_and_special_members.cpp

#include <gtest/gtest.h>

#include <charconv>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>

namespace {

struct Point {
  int x;
  bool operator==(const Point&) const = default;
};

std::string encode(const Point& point) {
  return "Point:" + std::to_string(point.x);
}

Point decode(const std::string& text) {
  constexpr std::string_view prefix = "Point:";
  constexpr std::size_t prefix_size = 6;
  if (text.size() < prefix_size ||
      std::string_view{text}.substr(0, prefix_size) != prefix) {
    throw std::invalid_argument{"invalid Point"};
  }

  int value = 0;
  const char* begin = text.data() + prefix_size;
  const char* end = text.data() + text.size();
  const auto result = std::from_chars(begin, end, value);
  if (result.ptr == begin || result.ec != std::errc{} || result.ptr != end) {
    throw std::invalid_argument{"invalid Point"};
  }
  return Point{value};
}

TEST(SerializationConcept, DomainFormatNeedsExplicitEncoderAndDecoder) {
  Point original{3};

  EXPECT_EQ(decode(encode(original)), original);
  EXPECT_EQ(decode("Point:-7"), (Point{-7}));
}

TEST(SerializationConcept, DecoderRejectsTruncatedMalformedAndOutOfRangeInput) {
  EXPECT_THROW(decode(""), std::invalid_argument);
  EXPECT_THROW(decode("Point"), std::invalid_argument);
  EXPECT_THROW(decode("Point:"), std::invalid_argument);
  EXPECT_THROW(decode("Other:3"), std::invalid_argument);
  EXPECT_THROW(decode("Point:no"), std::invalid_argument);
  EXPECT_THROW(decode("Point:3tail"), std::invalid_argument);
  EXPECT_THROW(decode("Point:999999999999999999999999"), std::invalid_argument);
}

TEST(SerializationConcept, ValueCopyAndSharedPointerCopyPreserveDifferentGraphs) {
  Point original{3};
  Point copied = original;
  auto shared = std::make_shared<Point>(Point{3});
  auto alias = shared;

  EXPECT_EQ(copied, original);
  EXPECT_NE(&copied, &original);
  EXPECT_EQ(alias.get(), shared.get());
}

TEST(SerializationConcept, MoveTransfersOwnedStateWithinTheProcess) {
  auto original = std::make_unique<Point>(Point{3});
  auto moved = std::move(original);

  EXPECT_EQ(original, nullptr);
  ASSERT_NE(moved, nullptr);
  EXPECT_EQ(moved->x, 3);
}

TEST(SerializationConcept, StandardCppHasNoUniversalObjectSerializationProtocol) {
  static_assert(std::is_trivially_copyable_v<Point>);

  // 即使 trivially copyable，直接持久化对象字节仍受布局、端序和版本约束；需定义格式。
}

}  // namespace
