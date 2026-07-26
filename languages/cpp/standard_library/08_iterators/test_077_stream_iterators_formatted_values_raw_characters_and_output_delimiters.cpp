// polyglot-covers:
// - cpp.stdlib.iterators.istream-iterator-formatted-extraction-and-default-end
// - cpp.stdlib.iterators.istream-iterator-single-pass-and-postincrement-proxy
// - cpp.stdlib.iterators.istream-iterator-parse-failure-becomes-end
// - cpp.stdlib.iterators.ostream-iterator-delimiter-after-every-value
// - cpp.stdlib.iterators.istreambuf-iterator-unformatted-character-traversal
// - cpp.stdlib.iterators.istreambuf-iterator-single-pass-end-and-whitespace
// - cpp.stdlib.iterators.ostreambuf-iterator-raw-output-and-failed-state
// - cpp.stdlib.iterators.stream-iterators-with-classic-algorithms

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

namespace {

TEST(IstreamIterator, FormattedExtractionReadsValuesAndDefaultConstructionMakesEnd) {
  std::istringstream input{"10  20\n30"};
  std::istream_iterator<int> first{input};
  std::istream_iterator<int> last;
  std::vector<int> values;

  for (; first != last; ++first) {
    values.push_back(*first);
  }

  EXPECT_EQ(values, (std::vector<int>{10, 20, 30}));
  EXPECT_TRUE(input.eof());

  // istream_iterator<T> 使用 operator>> 做格式化提取，默认 skipws，因此多个空白被跳过。
  // 默认构造对象是 end-of-stream sentinel；读到 EOF 或提取失败后 iterator 与它相等。
}

TEST(IstreamIterator, ItIsSinglePassAndPostincrementPreservesTheOldValue) {
  std::istringstream input{"7 11"};
  std::istream_iterator<int> iterator{input};

  static_assert(std::input_iterator<decltype(iterator)>);
  static_assert(!std::forward_iterator<decltype(iterator)>);

  auto previous = iterator++;
  EXPECT_EQ(*previous, 7);
  EXPECT_EQ(*iterator, 11);

  // postfix increment 的返回对象/代理保存递增前的值，支持 `*it++` 惯用法；但 iterator
  // 副本共享同一个 stream，推进一份会消费公共输入，不能按多遍 forward iterator 使用。
}

TEST(IstreamIterator, ParseFailureStopsTheRangeAndLeavesStreamDiagnostics) {
  std::istringstream input{"1 invalid 2"};
  std::istream_iterator<int> iterator{input};
  const std::istream_iterator<int> end;

  ASSERT_NE(iterator, end);
  EXPECT_EQ(*iterator, 1);

  ++iterator;
  EXPECT_EQ(iterator, end);
  EXPECT_TRUE(input.fail());
  EXPECT_FALSE(input.eof());

  input.clear();
  std::string invalid;
  input >> invalid;
  EXPECT_EQ(invalid, "invalid");

  // 类型转换失败与真正 EOF 都让 iterator 到达 end，区别要查看 stream state。
  // clear() 只清状态，不丢弃坏 token；恢复解析时还需读取或忽略导致失败的输入。
}

TEST(StreamIterators, ClassicCopyCanBridgeFormattedInputAndOutput) {
  std::istringstream input{"2 3 5"};
  std::ostringstream output;

  std::copy(
      std::istream_iterator<int>{input},
      std::istream_iterator<int>{},
      std::ostream_iterator<int>{output, ":"});

  EXPECT_EQ(output.str(), "2:3:5:");

  // 输入/输出迭代器让经典算法连接 stream；ostream_iterator 的 delimiter 在每次值之后
  // 写出，所以最后也有冒号。它不是只写“元素之间”的 join 分隔符。
}

TEST(OstreamIterator, AssignmentUsesFormattedInsertionAndIncrementIsANoOp) {
  std::ostringstream output;
  auto iterator = std::ostream_iterator<double>{output, "|"};

  *iterator = 1.5;
  ++iterator;
  iterator++;
  *iterator = 2.25;

  EXPECT_EQ(output.str(), "1.5|2.25|");

  // `*out=value` 调用 `stream << value` 后再写 delimiter；operator* 和 ++ 都只返回自身。
  // 格式由 stream flags、locale 与 T 的 operator<< 决定，不由 iterator 自己格式化。
}

TEST(IstreambufIterator, ItReadsRawCharactersIncludingWhitespace) {
  std::istringstream input{"a b\nc"};
  std::istreambuf_iterator<char> first{input};
  std::istreambuf_iterator<char> last;

  std::string raw(first, last);

  EXPECT_EQ(raw, "a b\nc");

  // istreambuf_iterator 直接读取 streambuf 字符，不执行 operator>>、skipws 或数值解析。
  // 它适合字节/字符搬运；若要文本编码解码或 token 语义，需要更高层处理。
}

TEST(IstreambufIterator, ItIsSinglePassAndDefaultEndRepresentsEndOfBuffer) {
  std::istringstream input{"xy"};
  std::istreambuf_iterator<char> iterator{input};
  const std::istreambuf_iterator<char> end;

  static_assert(std::input_iterator<decltype(iterator)>);
  static_assert(!std::forward_iterator<decltype(iterator)>);

  EXPECT_EQ(*iterator, 'x');
  ++iterator;
  EXPECT_EQ(*iterator, 'y');
  ++iterator;
  EXPECT_EQ(iterator, end);

  // streambuf 的 get area 是共享可消费状态，所以它仍是单遍 input iterator。
  // 到达 sgetc()==Traits::eof() 后与默认 end 相等，不能再解引用。
}

TEST(OstreambufIterator, ItWritesRawCharactersAndReportsBufferFailure) {
  std::ostringstream output;
  std::ostreambuf_iterator<char> iterator{output};
  const std::string source = "a b\n";

  auto result = std::copy(source.begin(), source.end(), iterator);

  EXPECT_EQ(output.str(), source);
  EXPECT_FALSE(result.failed());

  // ostreambuf_iterator 逐字符调用 sputc，不做格式化也不添加 delimiter。failed() 表示
  // 某次写入返回 Traits::eof；仍应结合 owning stream 的状态处理真实 I/O 错误。
}

}  // namespace
