// polyglot-covers:
// - cpp.stdlib.io.formatted-output-integer-base-sign-prefix-and-uppercase
// - cpp.stdlib.io.formatted-output-alignment-fill-width-and-reset
// - cpp.stdlib.io.formatted-output-floating-format-and-precision
// - cpp.stdlib.io.formatted-output-bool-character-pointer-and-cxx20-volatile-trap
// - cpp.stdlib.io.ostream-put-write-and-embedded-null
// - cpp.stdlib.io.ostream-flush-endl-ends-and-unitbuf
// - cpp.stdlib.io.quoted-output-default-and-custom-delimiters
// - cpp.stdlib.io.ostream-streambuf-transfer
// - cpp.stdlib.io.ostream-tellp-seekp-and-overwrite
// - cpp.stdlib.io.custom-inserter-state-preservation-and-error-propagation

#include <gtest/gtest.h>

#include <array>
#include <iomanip>
#include <ios>
#include <ostream>
#include <sstream>
#include <string>
#include <type_traits>

namespace {

class CountingStringBuffer : public std::stringbuf {
 public:
  int sync_calls() const { return sync_calls_; }

 protected:
  int sync() override {
    ++sync_calls_;
    return std::stringbuf::sync();
  }

 private:
  int sync_calls_ = 0;
};

struct Coordinate {
  int x;
  int y;
};

std::ostream& operator<<(std::ostream& output, const Coordinate& coordinate) {
  std::ostream::sentry sentry{output};
  if (!sentry) {
    return output;
  }

  const auto flags = output.flags();
  const auto fill = output.fill();
  const auto precision = output.precision();
  output << std::dec << '(' << coordinate.x << ", " << coordinate.y << ')';
  output.flags(flags);
  output.fill(fill);
  output.precision(precision);
  return output;
}

template <class Value>
concept OstreamInsertable = requires(std::ostream& output, Value value) { output << value; };

TEST(FormattedOutputIntegers, BasePrefixSignAndUppercaseComposeThroughFlags) {
  std::ostringstream output;

  output << std::showbase << std::uppercase << std::hex << 255 << ' ' << std::oct << 8
         << ' ' << std::dec << std::showpos << 42;

  EXPECT_EQ(output.str(), "0XFF 010 +42");

  // hex/oct/dec 持续改变 basefield；showbase 控制非十进制前缀，uppercase 也影响
  // 十六进制数字和指数。showpos 对非负十进制数添加 '+'，不会改变数值。
}

TEST(FormattedOutputAlignment, WidthAppliesOnceAndInternalKeepsSignBeforePadding) {
  std::ostringstream output;

  output << std::setfill('.') << std::setw(6) << std::right << 42 << '|';
  output << std::setw(6) << std::left << 42 << '|';
  output << std::showpos << std::internal << std::setw(6) << 42 << '|';
  output << 7;

  EXPECT_EQ(output.str(), "....42|42....|+...42|+7");
  EXPECT_EQ(output.width(), 0);
  EXPECT_EQ(output.fill(), '.');

  // setw/width 只作用于下一次会消费宽度的格式化插入，随后归零；fill 和对齐标志
  // 持续保留。internal 把符号/基数前缀放前面，把填充放在前缀与数字之间。
}

TEST(FormattedOutputFloating, PrecisionMeaningDependsOnTheSelectedFloatfield) {
  std::ostringstream output;
  output << std::setprecision(4) << std::defaultfloat << 12.34567 << '|';
  output << std::fixed << 12.34567 << '|';
  output << std::scientific << 12.34567 << '|';
  output << std::hexfloat << 3.0;

  const std::string text = output.str();
  EXPECT_EQ(text.substr(0, text.find('|')), "12.35");
  EXPECT_NE(text.find("12.3457"), std::string::npos);
  EXPECT_NE(text.find("1.2346e+01"), std::string::npos);
  EXPECT_NE(text.find("0x1.8p+1"), std::string::npos);

  // defaultfloat 的 precision 是有效数字数；fixed/scientific 是小数点后位数。
  // hexfloat 忽略普通 precision 规则并输出十六进制有效数与二进制指数。
}

TEST(FormattedOutputScalarKinds, BoolCharacterAndCxx20VolatilePointerChooseDifferentOverloads) {
  volatile int object = 7;
  volatile int* pointer = &object;
  std::ostringstream output;

  output << std::boolalpha << true << ' ' << 'A' << ' ' << static_cast<int>('A') << ' '
         << pointer;

  EXPECT_EQ(output.str(), "true A 65 true");
  static_assert(!OstreamInsertable<char8_t>);

  // char 按字符输出，显式转成 int 才输出编码值。C++20 没有 const volatile void*
  // 指针重载，volatile T* 会退而转换成 bool；该缺口到 C++23 才补上。
  // char8_t 插入重载则被删除，避免把 UTF-8 代码单元误当普通 char 直接输出。
}

TEST(UnformattedOutput, PutAndWritePreserveWhitespaceAndEmbeddedNulls) {
  std::ostringstream output;
  const std::array<char, 5> data{'A', '\0', 'B', '\n', 'C'};

  output.put('>');
  output.write(data.data(), data.size());

  const std::string result = output.str();
  ASSERT_EQ(result.size(), 6U);
  EXPECT_EQ(result[0], '>');
  EXPECT_EQ(result[2], '\0');
  EXPECT_EQ(result.substr(3), "B\nC");

  // write 按明确 streamsize 写原始 CharT 序列，不在零字符停止，也不做数字或
  // locale 格式化。count 必须真实可读；越界仍是调用者的前置条件责任。
}

TEST(OutputFlush, FlushEndlEndsAndUnitbufHaveDifferentCommitBehavior) {
  CountingStringBuffer buffer;
  std::ostream output{&buffer};

  output << 'a';
  EXPECT_EQ(buffer.sync_calls(), 0);
  output << std::flush;
  EXPECT_EQ(buffer.sync_calls(), 1);
  output << std::endl;
  EXPECT_EQ(buffer.sync_calls(), 2);
  output << std::ends;
  EXPECT_EQ(buffer.sync_calls(), 2);
  EXPECT_EQ(buffer.str(), std::string("a\n\0", 3));

  output << std::unitbuf << 'x';
  EXPECT_EQ(buffer.sync_calls(), 3);
  output << 'y' << std::nounitbuf;
  EXPECT_EQ(buffer.sync_calls(), 4);

  // flush 只同步；endl 先写换行再同步；ends 写零字符但不 flush。unitbuf 让每次
  // 格式化输出的 sentry 析构时同步，适合诊断但会显著增加 I/O 开销。
}

TEST(QuotedOutput, ItAddsDelimitersAndEscapesOnlyTheConfiguredCharacters) {
  std::ostringstream output;
  output << std::quoted("a \"quote\" \\ path") << ' '
         << std::quoted("x'y", '\'', '\\');

  EXPECT_EQ(output.str(), R"("a \"quote\" \\ path" 'x\'y')");

  // quoted 只转义 delimiter 与 escape 自身；它不会替换换行、控制字符或 Unicode，
  // 因而不是 JSON 编码器。相同 delimiter/escape 配置可由输入端无损读回。
}

TEST(StreambufInsertion, InsertingABufferTransfersUntilEofAndReportsAnEmptyTransfer) {
  std::istringstream source{"payload"};
  std::ostringstream destination;

  destination << source.rdbuf();
  EXPECT_EQ(destination.str(), "payload");
  EXPECT_TRUE(destination.good());
  EXPECT_TRUE(source.eof() || source.rdbuf()->sgetc() == std::char_traits<char>::eof());

  std::istringstream empty{""};
  std::ostringstream failed;
  failed << empty.rdbuf();
  EXPECT_TRUE(failed.fail());

  // operator<<(streambuf*) 逐字符转移，至少一个字符失败/异常时按规则设置状态。
  // 它消费源缓冲区位置，却不一定修改拥有源缓冲区的 istream 状态位。
}

TEST(OutputSeeking, TellpAndSeekpRepositionThePutPointerForOverwrite) {
  std::ostringstream output;
  output << "abcdef";
  EXPECT_EQ(output.tellp(), std::streampos{6});

  output.seekp(2);
  output << "XY";
  EXPECT_EQ(output.tellp(), std::streampos{4});
  EXPECT_EQ(output.str(), "abXYef");

  output.seekp(-1, std::ios_base::end);
  output.put('!');
  EXPECT_EQ(output.str(), "abXYe!");

  // seekp 移动写位置而不自动截断字符串；在中间写会覆盖已有字符。失败位置由
  // failbit 与 streampos(-1) 表达，偏移单位由具体 streambuf 决定。
}

TEST(CustomInserter, ItRestoresFormattingStateAndLeavesStreamErrorsVisible) {
  std::ostringstream output;
  output << std::hex << std::setfill('*') << std::setprecision(3);
  const auto before_flags = output.flags();

  output << Coordinate{10, 15} << ' ' << 16;

  EXPECT_EQ(output.str(), "(10, 15) 10");
  EXPECT_EQ(output.flags(), before_flags);
  EXPECT_EQ(output.fill(), '*');
  EXPECT_EQ(output.precision(), 3);

  std::ostream broken{nullptr};
  broken << Coordinate{1, 2};
  EXPECT_TRUE(broken.bad());

  // 自定义 inserter 先建 sentry，让坏流直接短路；临时改变格式后恢复，避免污染
  // 调用者。不要捕获并吞掉底层输出错误，流状态必须继续向链式调用传播。
}

}  // namespace
