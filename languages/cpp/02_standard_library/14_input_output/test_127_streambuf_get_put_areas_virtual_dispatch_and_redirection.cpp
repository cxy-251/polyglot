// polyglot-covers:
// - cpp.stdlib.io.streambuf-sgetc-sbumpc-snextc-and-eof
// - cpp.stdlib.io.streambuf-sputbackc-sungetc-and-putback-failure
// - cpp.stdlib.io.streambuf-sputc-sputn-and-overflow
// - cpp.stdlib.io.streambuf-underflow-get-area-refill-protocol
// - cpp.stdlib.io.streambuf-overflow-xsputn-and-sync-protocol
// - cpp.stdlib.io.streambuf-pubimbue-and-locale
// - cpp.stdlib.io.streambuf-pubseekoff-pubseekpos-and-failure-position
// - cpp.stdlib.io.basic-ios-rdbuf-redirection-and-state
// - cpp.stdlib.io.streambuf-eof-int-type-domain

#include <gtest/gtest.h>

#include <algorithm>
#include <cctype>
#include <ios>
#include <locale>
#include <ostream>
#include <sstream>
#include <streambuf>
#include <string>
#include <string_view>

namespace {

class OneCharacterAtATimeBuffer : public std::streambuf {
 public:
  explicit OneCharacterAtATimeBuffer(std::string source) : source_(std::move(source)) {}

  int underflow_calls() const { return underflow_calls_; }

 protected:
  int_type underflow() override {
    ++underflow_calls_;
    if (next_ == source_.size()) {
      return traits_type::eof();
    }
    current_ = source_[next_++];
    setg(&current_, &current_, &current_ + 1);
    return traits_type::to_int_type(current_);
  }

 private:
  std::string source_;
  std::size_t next_ = 0;
  char current_ = '\0';
  int underflow_calls_ = 0;
};

class UppercaseOutputBuffer : public std::streambuf {
 public:
  const std::string& text() const { return text_; }
  int overflow_calls() const { return overflow_calls_; }
  int sync_calls() const { return sync_calls_; }

 protected:
  int_type overflow(int_type value) override {
    ++overflow_calls_;
    if (traits_type::eq_int_type(value, traits_type::eof())) {
      return traits_type::not_eof(value);
    }
    const auto character = static_cast<unsigned char>(traits_type::to_char_type(value));
    text_.push_back(static_cast<char>(std::toupper(character)));
    return value;
  }

  std::streamsize xsputn(const char* source, std::streamsize count) override {
    for (std::streamsize index = 0; index < count; ++index) {
      const auto character = static_cast<unsigned char>(source[index]);
      text_.push_back(static_cast<char>(std::toupper(character)));
    }
    return count;
  }

  int sync() override {
    ++sync_calls_;
    return 0;
  }

 private:
  std::string text_;
  int overflow_calls_ = 0;
  int sync_calls_ = 0;
};

class RejectingOutputBuffer : public std::streambuf {};

TEST(StreambufInput, PeekConsumeAdvanceAndEndUseTheTraitsIntTypeProtocol) {
  std::stringbuf buffer{"abc", std::ios_base::in};
  using Traits = std::char_traits<char>;

  EXPECT_EQ(Traits::to_char_type(buffer.sgetc()), 'a');
  EXPECT_EQ(Traits::to_char_type(buffer.sgetc()), 'a');
  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'a');
  EXPECT_EQ(Traits::to_char_type(buffer.snextc()), 'c');
  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'c');
  EXPECT_TRUE(Traits::eq_int_type(buffer.sgetc(), Traits::eof()));

  // sgetc 只看当前字符；sbumpc 返回后前进；snextc 先前进再看新字符。返回 int_type
  // 才能同时表达所有 char 值与 EOF，不应先窄化再判断结束。
}

TEST(StreambufPutback, PutbackCanReplaceACharacterButTheBufferMayRejectIt) {
  std::stringbuf buffer{"abc", std::ios_base::in | std::ios_base::out};
  using Traits = std::char_traits<char>;

  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'a');
  EXPECT_EQ(Traits::to_char_type(buffer.sputbackc('A')), 'A');
  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'A');
  EXPECT_EQ(Traits::to_char_type(buffer.sungetc()), 'A');
  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'A');

  std::stringbuf at_begin{"x", std::ios_base::in};
  EXPECT_TRUE(Traits::eq_int_type(at_begin.sungetc(), Traits::eof()));

  // putback/unget 是否成功由缓冲区控制；退到开头或替换不可修改的外部序列都可能
  // 失败。输入解析器只能做有限回退，不能把它当任意随机访问接口。
}

TEST(StreambufOutput, SputcAndSputnDelegateToThePutAreaOrVirtualOperations) {
  UppercaseOutputBuffer buffer;
  using Traits = std::char_traits<char>;

  EXPECT_FALSE(Traits::eq_int_type(buffer.sputc('a'), Traits::eof()));
  EXPECT_EQ(buffer.sputn("bcD", 3), 3);
  EXPECT_EQ(buffer.text(), "ABCD");
  EXPECT_EQ(buffer.overflow_calls(), 1);

  RejectingOutputBuffer rejecting;
  EXPECT_TRUE(Traits::eq_int_type(rejecting.sputc('x'), Traits::eof()));

  // 没有可用 put area 时 sputc 调 overflow；批量 sputn 通常调 xsputn。默认 overflow
  // 拒绝字符并返回 EOF，因此自定义输出缓冲区至少要实现一种写入路径。
}

TEST(StreambufUnderflow, ARefilledGetAreaPreventsRepeatedVirtualCallsUntilConsumed) {
  OneCharacterAtATimeBuffer buffer{"xy"};
  using Traits = std::char_traits<char>;

  EXPECT_EQ(Traits::to_char_type(buffer.sgetc()), 'x');
  EXPECT_EQ(Traits::to_char_type(buffer.sgetc()), 'x');
  EXPECT_EQ(buffer.underflow_calls(), 1);

  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'x');
  EXPECT_EQ(Traits::to_char_type(buffer.sgetc()), 'y');
  EXPECT_EQ(buffer.underflow_calls(), 2);
  EXPECT_EQ(Traits::to_char_type(buffer.sbumpc()), 'y');
  EXPECT_TRUE(Traits::eq_int_type(buffer.sgetc(), Traits::eof()));
  EXPECT_EQ(buffer.underflow_calls(), 3);

  // underflow 应准备 get area 但不消费字符。只要 gptr()<egptr()，基类直接读取，
  // 不再次虚调用；耗尽后才请求下一块。这是网络/解压流缓冲的核心协议。
}

TEST(StreambufSync, PubSyncMapsZeroToSuccessAndStreamsUseItForFlush) {
  UppercaseOutputBuffer buffer;
  std::ostream output{&buffer};

  output << "hello";
  EXPECT_EQ(buffer.sync_calls(), 0);
  output.flush();
  EXPECT_EQ(buffer.sync_calls(), 1);
  EXPECT_TRUE(output.good());

  // pubsync 调虚函数 sync；约定 0 成功、-1 失败。flush 只要求缓冲区把待处理字符
  // 提交到受控序列，不保证磁盘已经完成物理持久化。
}

TEST(StreambufLocale, PubimbueInstallsALocaleAndReturnsThePreviousOne) {
  std::stringbuf buffer;
  const auto old = buffer.pubimbue(std::locale::classic());

  EXPECT_EQ(buffer.getloc(), std::locale::classic());
  EXPECT_EQ(old, std::locale::classic());

  // pubimbue 先让派生缓冲区处理 locale 变化，再保存新 locale。若缓冲区正在做
  // 有状态转码，标准限制在首次 I/O 后随意 imbue，避免破坏当前位置的转换状态。
}

TEST(StreambufPositioning, StringbufSupportsSeekingAndReportsInvalidRequestsWithMinusOne) {
  std::stringbuf buffer{"abcdef", std::ios_base::in | std::ios_base::out};
  const std::streampos failure{std::streamoff{-1}};

  EXPECT_EQ(buffer.pubseekpos(std::streampos{2}, std::ios_base::in), std::streampos{2});
  EXPECT_EQ(std::char_traits<char>::to_char_type(buffer.sbumpc()), 'c');
  EXPECT_EQ(
      buffer.pubseekoff(-1, std::ios_base::end, std::ios_base::in),
      std::streampos{5});
  EXPECT_EQ(std::char_traits<char>::to_char_type(buffer.sgetc()), 'f');
  EXPECT_EQ(
      buffer.pubseekpos(std::streampos{99}, std::ios_base::in),
      failure);

  // seekoff 使用相对方向，seekpos 使用先前取得的位置；失败以 streampos(-1) 表示。
  // 同时定位 in/out 序列可能受派生缓冲区额外限制，不要假定两个指针永远同步。
}

TEST(StreamRedirection, ReplacingRdbufChangesTheDestinationWithoutCopyingTheStream) {
  std::ostringstream original;
  UppercaseOutputBuffer redirected;
  std::ostream output{original.rdbuf()};

  auto* previous = output.rdbuf(&redirected);
  EXPECT_EQ(previous, original.rdbuf());
  EXPECT_TRUE(output.good());

  output << "mixed Case";
  output.flush();
  EXPECT_EQ(redirected.text(), "MIXED CASE");
  EXPECT_EQ(original.str(), "");

  EXPECT_EQ(output.rdbuf(previous), &redirected);
  output << "restored";
  EXPECT_EQ(original.str(), "restored");

  // ostream 不拥有通过 rdbuf(pointer) 安装的缓冲区；恢复和析构顺序由调用者负责。
  // 替换为非空缓冲区会 clear 状态，适合受控重定向，但并非线程安全的全局日志切换。
}

TEST(StreambufEof, TraitsHelpersAreTheOnlyPortableWayToCompareEndMarkers) {
  using Traits = std::char_traits<char>;
  std::stringbuf empty{"", std::ios_base::in};
  const auto value = empty.sgetc();

  EXPECT_TRUE(Traits::eq_int_type(value, Traits::eof()));
  EXPECT_FALSE(Traits::eq_int_type(Traits::not_eof(value), Traits::eof()));

  // 直接写 value == -1 假定了 EOF 的具体编码；自定义 traits 只承诺 eof、not_eof
  // 与 eq_int_type 协同工作。
}

}  // namespace
