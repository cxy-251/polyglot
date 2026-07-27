// 未对齐访问、视图生命周期与复制边界。
// 共同问题：多字节访问是否要求对齐；共享视图何时阻止或失去底层存储；
// 协议读取如何避免依赖宿主对象布局。
//
// polyglot-family: text_binary_and_serialization
// polyglot-concept: binary_buffers_views_and_endianness
// polyglot-related: languages/cpp/language/test_017_object_representation_alignment_and_bit_cast.cpp
// polyglot-related: languages/cpp/standard_library/07_containers/
// polyglot-related+: test_063_array_and_span_fixed_storage_non_owning_views_and_bytes.cpp

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>
#include <vector>

namespace {

TEST(BinaryAlignmentConcept, MemcpyRoundTripDoesNotRequireAnAlignedSourcePointer) {
  const std::uint32_t original = 0x01020304;
  std::array<std::byte, sizeof(original) + 1> storage{};
  std::uint32_t decoded = 0;

  std::memcpy(storage.data() + 1, &original, sizeof(original));
  std::memcpy(&decoded, storage.data() + 1, sizeof(decoded));

  EXPECT_EQ(decoded, original);
  EXPECT_GT(alignof(std::uint32_t), alignof(std::byte));

  // storage + 1 不承诺满足 uint32_t 对齐；memcpy 按对象表示复制合法。把该地址
  // reinterpret_cast 为 uint32_t* 后解引用可能违反对齐和别名规则，不能执行演示。
}

TEST(BinaryAlignmentConcept, OwnedCopySurvivesAfterTheViewSourceChanges) {
  std::vector<std::uint8_t> storage{1, 2, 3};
  std::span<std::uint8_t> view = storage;
  const std::vector<std::uint8_t> copied{view.begin(), view.end()};

  view[0] = 9;

  EXPECT_EQ(storage, (std::vector<std::uint8_t>{9, 2, 3}));
  EXPECT_EQ(copied, (std::vector<std::uint8_t>{1, 2, 3}));

  // span 不拥有或固定底层存储；其生命周期必须短于 storage，vector 重分配后旧 span
  // 会悬空。需要跨生命周期保存数据时应建立拥有型副本。
}

}  // namespace
