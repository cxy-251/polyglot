// polyglot-covers:
// - cpp.stdlib.io.unformatted-input-get-peek-gcount-and-delimiter
// - cpp.stdlib.io.istream-member-getline-buffer-limit-and-state
// - cpp.stdlib.io.free-getline-string-final-line-and-eof
// - cpp.stdlib.io.istream-read-short-read-state-and-gcount
// - cpp.stdlib.io.istream-readsome-available-data-and-zero-not-eof
// - cpp.stdlib.io.istream-ignore-count-delimiter-and-unbounded-count
// - cpp.stdlib.io.istream-unget-putback-success-and-failure
// - cpp.stdlib.io.istream-get-to-streambuf-leaves-delimiter
// - cpp.stdlib.io.tellg-seekg-clear-state-and-reposition
// - cpp.stdlib.io.unformatted-input-state-machine-traps

#include <gtest/gtest.h>

#include <array>
#include <ios>
#include <limits>
#include <sstream>
#include <string>

namespace {

TEST(UnformattedGet, GetConsumesOneCharacterWhilePeekLeavesItAndUpdatesGcountDifferently) {
  std::istringstream input{" abc"};

  EXPECT_EQ(input.peek(), ' ');
  EXPECT_EQ(input.gcount(), 0);

  char first = '\0';
  input.get(first);
  EXPECT_EQ(first, ' ');
  EXPECT_EQ(input.gcount(), 1);
  EXPECT_EQ(input.get(), 'a');
  EXPECT_EQ(input.gcount(), 1);

  // 非格式化 get 不受 skipws 影响，空格也是数据。peek 不提取字符，因此 gcount
  // 为 0；每次非格式化操作都会覆盖而不是累积上一次 gcount。
}

TEST(MemberGetline, ItConsumesTheDelimiterButDoesNotStoreIt) {
  std::istringstream input{"alpha,beta"};
  std::array<char, 16> buffer{};

  input.getline(buffer.data(), buffer.size(), ',');

  EXPECT_STREQ(buffer.data(), "alpha");
  EXPECT_EQ(input.gcount(), 6);
  EXPECT_EQ(input.peek(), 'b');

  // basic_istream::getline 的 gcount 包含已消费的分隔符，目标字符串不包含它。
  // 这与 free std::getline 写入 string 的接口相似，但缓冲区满时状态规则不同。
}

TEST(MemberGetline, FullBufferWritesATerminatorSetsFailbitAndLeavesRemainingInput) {
  std::istringstream input{"abcdef\n"};
  std::array<char, 4> buffer{};

  input.getline(buffer.data(), buffer.size());

  EXPECT_STREQ(buffer.data(), "abc");
  EXPECT_EQ(input.gcount(), 3);
  EXPECT_TRUE(input.fail());

  input.clear();
  EXPECT_EQ(input.peek(), 'd');

  // 最多存 n-1 个字符并补零；未遇到分隔符便填满数组会置 failbit，剩余字符还在
  // 流中。固定数组读取任意长度行容易产生分段逻辑，通常应使用 string getline。
}

TEST(FreeGetline, LastLineWithoutDelimiterIsStillSuccessfulAndAlsoSetsEofbit) {
  std::istringstream input{"first\nlast"};
  std::string line;

  ASSERT_TRUE(static_cast<bool>(std::getline(input, line)));
  EXPECT_EQ(line, "first");
  EXPECT_TRUE(input.good());

  ASSERT_TRUE(static_cast<bool>(std::getline(input, line)));
  EXPECT_EQ(line, "last");
  EXPECT_TRUE(input.eof());
  EXPECT_FALSE(input.fail());

  EXPECT_FALSE(static_cast<bool>(std::getline(input, line)));
  EXPECT_TRUE(input.fail());

  // 最后一行不必以换行结束；只要提取到字符，本次 getline 就成功，可能同时置
  // eofbit。下一次在 EOF 且无字符时才再置 failbit。
}

TEST(UnformattedRead, ShortReadKeepsThePrefixAndSetsBothEofAndFail) {
  std::istringstream input{"abc"};
  std::array<char, 5> buffer{'?', '?', '?', '?', '?'};

  input.read(buffer.data(), buffer.size());

  EXPECT_EQ(input.gcount(), 3);
  EXPECT_EQ(buffer[0], 'a');
  EXPECT_EQ(buffer[2], 'c');
  EXPECT_EQ(buffer[3], '?');
  EXPECT_TRUE(input.eof());
  EXPECT_TRUE(input.fail());

  // read 要求恰好 n 个字符；短读会保留已读前缀、用 gcount 报实际数量，并设置
  // eofbit|failbit。处理文件尾块时必须先消费 gcount，再判断状态。
}

TEST(UnformattedReadsome, ItReadsOnlyCurrentlyAvailableCharactersAndZeroIsNotEof) {
  std::istringstream input{"abcd"};
  std::array<char, 8> buffer{};

  const auto first = input.readsome(buffer.data(), 2);
  EXPECT_EQ(first, 2);
  EXPECT_EQ(std::string(buffer.data(), 2), "ab");
  EXPECT_TRUE(input.good());

  input.ignore(2);
  const auto none = input.readsome(buffer.data(), buffer.size());
  EXPECT_EQ(none, 0);
  EXPECT_FALSE(input.eof());

  // readsome 根据 rdbuf()->in_avail() 决定本次读取量；返回 0 只表示当前无可用字符，
  // 不可靠地表示永久 EOF，尤其不能用它实现阻塞流的完整读取循环。
}

TEST(UnformattedIgnore, CountAndDelimiterStopAtWhicheverComesFirst) {
  std::istringstream input{"header:payload\nnext"};

  input.ignore(100, ':');
  EXPECT_EQ(input.gcount(), 7);
  EXPECT_EQ(input.peek(), 'p');

  input.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
  EXPECT_EQ(input.peek(), 'n');

  // 被找到的 delimiter 会被消费并计入 gcount。使用 streamsize 最大值可表达“只看
  // 分隔符、不受普通计数限制”，常用于丢弃失败字段剩余行。
}

TEST(UnformattedPutback, UngetRestoresTheLastCharacterWhileReplacementMayFail) {
  std::istringstream input{"abc"};
  EXPECT_EQ(input.get(), 'a');
  input.unget();
  EXPECT_TRUE(input.good());
  EXPECT_EQ(input.get(), 'a');

  input.putback('A');
  EXPECT_TRUE(input.fail());
  input.clear();
  EXPECT_EQ(input.peek(), 'b');

  // istringstream 的只读缓冲区能 unget 原字符，但不能保证用 putback 替换成不同
  // 字符。回退失败会置 badbit；清状态后当前位置由底层缓冲区的失败协议决定。
}

TEST(UnformattedTransfer, GetToStreambufCopiesUntilDelimiterAndLeavesItPending) {
  std::istringstream input{"alpha,beta"};
  std::ostringstream output;

  input.get(*output.rdbuf(), ',');

  EXPECT_EQ(output.str(), "alpha");
  EXPECT_EQ(input.gcount(), 5);
  EXPECT_EQ(input.peek(), ',');

  input.get();
  input.get(*output.rdbuf());
  EXPECT_EQ(output.str(), "alphabeta");

  // get(streambuf, delim) 与 getline 不同：它复制分隔符之前的字符但保留分隔符。
  // 目标缓冲区拒绝写入或一个字符都未复制时会置 failbit。
}

TEST(InputSeeking, ClearErrorStateBeforeRepositioningAfterEndOfInput) {
  std::istringstream input{"012345"};
  std::array<char, 8> buffer{};

  input.read(buffer.data(), buffer.size());
  EXPECT_TRUE(input.fail());
  EXPECT_EQ(input.gcount(), 6);

  input.seekg(2);
  EXPECT_TRUE(input.fail());

  input.clear();
  input.seekg(2, std::ios_base::beg);
  ASSERT_TRUE(input.good());
  EXPECT_EQ(input.tellg(), std::streampos{2});
  EXPECT_EQ(input.get(), '2');

  input.seekg(-1, std::ios_base::end);
  EXPECT_EQ(input.get(), '5');

  // seekg 在构造 sentry 前会清 eofbit，但已有 failbit 仍阻止定位；先 clear 再 seek。
  // tellg 返回 streampos，失败是 streampos(-1)，不要先窄化成 int 再判断。
}

}  // namespace
