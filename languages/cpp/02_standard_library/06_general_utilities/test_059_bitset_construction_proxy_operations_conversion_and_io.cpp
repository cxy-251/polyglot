// polyglot-covers:
// - cpp.stdlib.utility.bitset-integer-and-string-construction
// - cpp.stdlib.utility.bitset-custom-zero-and-one-characters
// - cpp.stdlib.utility.bitset-reference-proxy
// - cpp.stdlib.utility.bitset-test-set-reset-and-flip
// - cpp.stdlib.utility.bitset-all-any-none-count-and-size
// - cpp.stdlib.utility.bitset-bitwise-and-shift-operations
// - cpp.stdlib.utility.bitset-string-and-integer-conversions
// - cpp.stdlib.utility.bitset-conversion-overflow
// - cpp.stdlib.utility.bitset-stream-io-and-hash
// - cpp.stdlib.utility.zero-length-bitset

#include <gtest/gtest.h>

#include <bitset>
#include <cstddef>
#include <functional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace {

TEST(Bitset, IntegerConstructionUsesTheLowBitsAndStringUsesRightmostAsBitZero) {
  const std::bitset<8> from_integer{0b1'0010'1101ULL};
  const std::bitset<8> from_string{"10110010"};

  EXPECT_EQ(from_integer.to_ulong(), 0b0010'1101UL);
  EXPECT_TRUE(from_integer[0]);
  EXPECT_FALSE(from_integer[7]);

  EXPECT_EQ(from_string.to_ulong(), 0b1011'0010UL);
  EXPECT_FALSE(from_string[0]);
  EXPECT_TRUE(from_string[7]);

  // 整数构造只取低 N 位，更高位被丢弃；字符串写法则把最右字符对应
  // bit 0，与人类通常的二进制书写顺序一致。operator[] 的索引也是从最低位开始。
}

TEST(Bitset, StringConstructionSupportsSubrangesAndCustomDigitCharacters) {
  const std::string source = "prefix-10110-suffix";
  const std::bitset<5> selected{source, 7, 5};
  const std::bitset<4> custom{std::string{"abba"}, 0, 4, 'a', 'b'};

  EXPECT_EQ(selected.to_string(), "10110");
  EXPECT_EQ(custom.to_string('a', 'b'), "abba");
  EXPECT_EQ(custom.to_ulong(), 0b0110UL);

  EXPECT_THROW((std::bitset<4>{std::string{"10x1"}}), std::invalid_argument);
  EXPECT_THROW(
      (std::bitset<4>{std::string{"101"}, 4}),
      std::out_of_range);

  // pos/count 先选字符子区间，再按 zero/one 字符解码。区间中出现其他字符
  // 抛 invalid_argument，pos 超过字符串长度抛 out_of_range；不是把非零字符都当成 1。
}

TEST(Bitset, MutableSubscriptReturnsAProxyThatWritesOneBit) {
  std::bitset<4> flags{"0010"};
  auto bit = flags[1];
  static_assert(
      std::is_same_v<decltype(bit), std::bitset<4>::reference>);

  EXPECT_TRUE(static_cast<bool>(bit));
  bit = false;
  EXPECT_EQ(flags.to_string(), "0000");
  bit.flip();
  EXPECT_EQ(flags.to_string(), "0010");
  flags[0] = flags[1];
  EXPECT_EQ(flags.to_string(), "0011");

  // bitset 不能返回 bool&，因为一个 bit 不是可独立寻址的 bool 对象。reference
  // proxy 把赋值、读取和 flip 转发到容器中的指定位；不应把 proxy 当成普通长寿命引用保存。
}

TEST(Bitset, CheckedTestAndBulkModifiersHaveDifferentInterfaces) {
  std::bitset<6> flags;
  EXPECT_TRUE(flags.none());

  flags.set(1).set(4);
  EXPECT_TRUE(flags.any());
  EXPECT_FALSE(flags.all());
  EXPECT_EQ(flags.count(), 2U);
  EXPECT_TRUE(flags.test(4));

  flags.flip(1);
  flags.reset(4);
  EXPECT_TRUE(flags.none());
  EXPECT_THROW((void)flags.test(flags.size()), std::out_of_range);

  flags.set();
  EXPECT_TRUE(flags.all());
  flags.flip();
  EXPECT_TRUE(flags.none());

  // test(pos) 做边界检查并抛 out_of_range，operator[] 要求 pos < N，越界不可用。
  // 无参 set/reset/flip 操作全部位，有 pos 参数的版本只修改一位且返回 *this 便于链式调用。
}

TEST(Bitset, BitwiseAndShiftOperatorsKeepTheFixedWidth) {
  const std::bitset<8> left{"11110000"};
  const std::bitset<8> right{"10101010"};

  EXPECT_EQ((left & right).to_string(), "10100000");
  EXPECT_EQ((left | right).to_string(), "11111010");
  EXPECT_EQ((left ^ right).to_string(), "01011010");
  EXPECT_EQ((~right).to_string(), "01010101");
  EXPECT_EQ((right << 2).to_string(), "10101000");
  EXPECT_EQ((right >> 3).to_string(), "00010101");

  std::bitset<8> mutable_bits = right;
  mutable_bits <<= 8;
  EXPECT_TRUE(mutable_bits.none());

  // bitset 宽度永远是 N：左移丢弃超出高位的 bit 并在低位补 0，右移相反。
  // 移动量大于或等于 N 会得到全 0，不会像内建整数的越界 shift 那样产生未定义行为。
}

TEST(Bitset, IntegerConversionThrowsWhenTheValueDoesNotFit) {
  std::bitset<65> too_wide;
  too_wide.set(64);

  EXPECT_THROW((void)too_wide.to_ullong(), std::overflow_error);
  EXPECT_EQ(std::bitset<8>{255}.to_ullong(), 255ULL);

  // to_ulong/to_ullong 不是无声截断；任何超出目标整数可表示范围的置位都使
  // 转换抛 overflow_error。相反，to_string 总能表示全部 N 位，是大位集的无损文本出口。
}

TEST(Bitset, StreamIoUsesExactlyTheVisibleBitCharacters) {
  const std::bitset<4> output_bits{"0101"};
  std::ostringstream output;
  output << output_bits;
  EXPECT_EQ(output.str(), "0101");

  std::istringstream input{"1101 tail"};
  std::bitset<4> input_bits;
  input >> input_bits;
  EXPECT_EQ(input_bits.to_ulong(), 13UL);

  const std::bitset<4> same{"1101"};
  EXPECT_EQ(
      std::hash<std::bitset<4>>{}(input_bits),
      std::hash<std::bitset<4>>{}(same));

  // 输出总写 N 个位字符。输入最多读 N 个当前 locale 定义的 0/1 字符，
  // 遇到其他字符就停止；流格式不会自动识别 0b 前缀或字节序。
}

TEST(Bitset, ZeroLengthSpecializationUsesVacuousTruthForAll) {
  const std::bitset<0> empty;

  EXPECT_EQ(empty.size(), 0U);
  EXPECT_EQ(empty.count(), 0U);
  EXPECT_FALSE(empty.any());
  EXPECT_TRUE(empty.none());
  EXPECT_TRUE(empty.all());
  EXPECT_EQ(empty.to_string(), "");

  // bitset<0> 是有效的零长度位集。all() 对空集为 true 是逻辑上的真空值：
  // 不存在任何一位违反“全部为 1”。这不意味着它真的包含一个置位 bit。
}

}  // namespace
