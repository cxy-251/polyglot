// polyglot-covers:
// - cpp.language.sizeof-alignof-and-alignas
// - cpp.language.object-and-value-representation
// - cpp.language.padding-bytes
// - cpp.language.trivially-copyable-memcpy
// - cpp.language.bit-cast
// - cpp.language.endianness
// - cpp.language.no-unique-address

#include <gtest/gtest.h>

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <type_traits>

namespace {

struct PaddedRecord {
  char marker;
  int value;
};

struct EmptyPolicy {};

struct PolicyOwner {
  [[no_unique_address]] EmptyPolicy policy;
  int value;
};

struct alignas(32) AlignedBlock {
  std::array<std::byte, 32> bytes;
};

TEST(ObjectRepresentation, SizeIncludesPaddingNeededForArrayElements) {
  EXPECT_GE(sizeof(PaddedRecord), sizeof(char) + sizeof(int));
  EXPECT_GE(alignof(PaddedRecord), alignof(char));
  EXPECT_GE(alignof(PaddedRecord), alignof(int));

  PaddedRecord records[2]{{'A', 1}, {'B', 2}};
  auto distance = reinterpret_cast<const std::byte*>(&records[1]) -
                  reinterpret_cast<const std::byte*>(&records[0]);
  EXPECT_EQ(distance, static_cast<std::ptrdiff_t>(sizeof(PaddedRecord)));

  // sizeof 包含内部和尾部 padding，确保数组相邻元素都满足对齐。padding 值未指定，
  // 因此不能用 memcmp 代替按成员相等比较普通结构体。
}

TEST(ObjectRepresentation, MemcpyRoundTripsATriviallyCopyableObject) {
  static_assert(std::is_trivially_copyable_v<PaddedRecord>);

  PaddedRecord source{'X', 42};
  PaddedRecord destination{};
  std::memcpy(&destination, &source, sizeof(source));

  EXPECT_EQ(destination.marker, 'X');
  EXPECT_EQ(destination.value, 42);

  // trivially copyable 类型可以把底层字节复制到另一个同类型对象再恢复值。这个许可不
  // 扩展到任意非平凡类，也不表示 padding 可用于稳定序列化或跨版本 ABI。
}

TEST(ObjectRepresentation, BitCastCopiesBitsWithoutAliasViolations) {
  float original = 12.5F;
  auto bytes = std::bit_cast<std::array<std::byte, sizeof(float)>>(original);
  float restored = std::bit_cast<float>(bytes);

  EXPECT_FLOAT_EQ(restored, original);

  static_assert(std::is_trivially_copyable_v<decltype(bytes)>);
  static_assert(sizeof(bytes) == sizeof(original));

  // bit_cast 要求源和目标大小相同且目标 trivially copyable。它按位复制，不通过 union
  // 读取 inactive member，也不创建违反 strict aliasing 的错误指针。
}

TEST(ObjectRepresentation, EndianReportsTheOrderOfScalarBytes) {
  constexpr std::uint32_t value = 0x0102'0304U;
  const auto bytes = std::bit_cast<std::array<std::uint8_t, 4>>(value);

  if constexpr (std::endian::native == std::endian::little) {
    EXPECT_EQ(bytes, (std::array<std::uint8_t, 4>{4, 3, 2, 1}));
  } else if constexpr (std::endian::native == std::endian::big) {
    EXPECT_EQ(bytes, (std::array<std::uint8_t, 4>{1, 2, 3, 4}));
  } else {
    EXPECT_NE(std::endian::native, std::endian::little);
    EXPECT_NE(std::endian::native, std::endian::big);
  }

  // std::endian 报告实现的标量字节顺序，不会自动转换数据。网络和文件格式仍应显式
  // 定义端序，并按字段编码，不能直接写出带 padding 的原始结构体内存。
}

TEST(Alignment, AlignasRaisesTheRequiredAlignment) {
  static_assert(alignof(AlignedBlock) >= 32);

  AlignedBlock block{};
  auto address = reinterpret_cast<std::uintptr_t>(&block);
  EXPECT_EQ(address % alignof(AlignedBlock), 0U);

  // alignas 可以提高声明的对齐，但不能请求比同一声明中其他约束更弱的有效对齐。
  // 过对齐动态对象还需要分配函数支持相应 alignment，标准 new 会处理合法类型要求。
}

TEST(ObjectRepresentation, NoUniqueAddressPermitsButDoesNotRequireOverlap) {
  static_assert(std::is_empty_v<EmptyPolicy>);

  PolicyOwner owner{{}, 7};
  EXPECT_EQ(owner.value, 7);
  EXPECT_GE(sizeof(PolicyOwner), sizeof(int));

  // [[no_unique_address]] 允许空成员与其他成员或 padding 共享地址，用于零开销策略对象。
  // 它不保证具体布局，代码不能通过地址相等与否推断成员存在或 ABI 结构。
}

}  // namespace
