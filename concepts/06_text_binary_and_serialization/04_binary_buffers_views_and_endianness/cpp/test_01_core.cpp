// 二进制缓冲区、视图与字节序。
// 共同问题：字节存储是否可变；视图是否共享内存；多字节整数如何选择端序；
// 复制与别名边界在哪里。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/cpp/language/test_017_object_representation_alignment_and_bit_cast.cpp

#include <gtest/gtest.h>

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>

namespace {

TEST(BinaryBuffersConcept, ByteArrayOwnsMutableStorage) {
  std::array<std::byte, 3> storage{
      std::byte{0x61},
      std::byte{0x62},
      std::byte{0x63},
  };

  storage[0] = std::byte{0x7A};

  EXPECT_EQ(std::to_integer<char>(storage[0]), 'z');
}

TEST(BinaryBuffersConcept, SpanIsANonOwningSharedView) {
  std::vector<std::uint8_t> storage{1, 2, 3};
  std::span<std::uint8_t> view = storage;

  view[1] = 9;

  EXPECT_EQ(storage[1], 9);
  EXPECT_EQ(view.data(), storage.data());
}

TEST(BinaryBuffersConcept, EndianReportsNativeObjectRepresentationOrder) {
  static_assert(
      std::endian::native == std::endian::little ||
      std::endian::native == std::endian::big);

  SUCCEED();
}

TEST(BinaryBuffersConcept, NetworkOrderMustBeEncodedExplicitly) {
  std::uint32_t value = 0x01020304;
  std::array<std::uint8_t, 4> big_endian{
      static_cast<std::uint8_t>(value >> 24),
      static_cast<std::uint8_t>(value >> 16),
      static_cast<std::uint8_t>(value >> 8),
      static_cast<std::uint8_t>(value),
  };

  EXPECT_EQ(big_endian, (std::array<std::uint8_t, 4>{1, 2, 3, 4}));
}

}  // namespace
