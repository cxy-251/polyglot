// polyglot-covers:
// - cpp.stdlib.io.istringstream-construction-extraction-and-str-replacement
// - cpp.stdlib.io.ostringstream-str-copy-and-output-only-sequence
// - cpp.stdlib.io.stringstream-shared-sequence-independent-get-put-positions
// - cpp.stdlib.io.string-stream-app-versus-ate-openmodes
// - cpp.stdlib.io.locked-libstdcxx-stringbuf-app-initial-position-gap
// - cpp.stdlib.io.string-stream-seek-overwrite-and-extension
// - cpp.stdlib.io.stringbuf-str-getter-setter-and-openmode
// - cpp.stdlib.io.cxx20-stringbuf-view-nonowning-lifetime
// - cpp.stdlib.io.cxx20-rvalue-str-move-and-string-setter
// - cpp.stdlib.io.string-stream-move-and-swap-buffer-ownership
// - cpp.stdlib.io.wide-string-stream-aliases

#include <gtest/gtest.h>

#include <ios>
#include <sstream>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>

namespace {

TEST(InputStringStream, ReplacingTheStringDoesNotClearExistingErrorState) {
  std::istringstream input{"bad"};
  int value = 0;
  input >> value;
  EXPECT_TRUE(input.fail());

  input.str("42");
  input >> value;
  EXPECT_TRUE(input.fail());

  input.clear();
  input >> value;
  EXPECT_EQ(value, 42);
  EXPECT_TRUE(input.eof());

  // str(new_text) 替换受控字符序列并重置缓冲区位置，但不清 basic_ios 的 rdstate。
  // 复用解析流时要同时设置新文本与 clear，否则新输入看似仍无法读取。
}

TEST(OutputStringStream, StrReturnsAnOwningCopyIndependentFromTheBuffer) {
  std::ostringstream output;
  output << "alpha" << 42;

  std::string copy = output.str();
  copy[0] = 'A';

  EXPECT_EQ(copy, "Alpha42");
  EXPECT_EQ(output.str(), "alpha42");

  // const lvalue 上的 str() 返回 owning string 副本；修改副本不会回写缓冲区。
  // 频繁取 str() 会反复分配复制，C++20 的 view() 可用于短期只读观察。
}

TEST(StringStream, GetAndPutPointersShareCharactersButMoveIndependently) {
  std::stringstream stream{"10 20", std::ios_base::in | std::ios_base::out};
  int first = 0;
  stream >> first;
  EXPECT_EQ(first, 10);
  EXPECT_EQ(stream.tellg(), std::streampos{2});

  stream.seekp(0, std::ios_base::end);
  stream << " 30";

  int second = 0;
  int third = 0;
  stream >> second >> third;
  EXPECT_EQ(second, 20);
  EXPECT_EQ(third, 30);

  // stringstream 的 get/put 指针位于同一字符序列，却是独立位置；写端追加不会自动
  // 把读端跳到开头或末尾。混合读写时显式使用 seekg/seekp 表达意图。
}

TEST(StringStreamModes, AppIsIgnoredByStringbufWhileAteChoosesInitialPosition) {
  std::ostringstream at_end{"seed", std::ios_base::out | std::ios_base::ate};
  at_end << 'X';
  EXPECT_EQ(at_end.str(), "seedX");
  at_end.seekp(0);
  at_end << 'Y';
  EXPECT_EQ(at_end.str(), "YeedX");

  std::ostringstream app_only{"seed", std::ios_base::out | std::ios_base::app};
  app_only << 'X';
  if (app_only.str() != "Xeed") {
    EXPECT_EQ(app_only.str(), "seedX");
    app_only.seekp(0);
    app_only << 'Y';
    EXPECT_EQ(app_only.str(), "YeedX");
    GTEST_SKIP()
        << "libstdc++ 11 treats app as an initial end position for stringbuf; "
           "N4861 [stringbuf.cons] only gives that effect to ate";
  }
  EXPECT_EQ(app_only.str(), "Xeed");

  // N4861 的 basic_stringbuf 初始化只解释 in/out/ate，app 不应影响 put 位置；
  // filebuf 的 app 才要求每次写前定位文件末尾。上面显式记录锁定实现的偏差。
}

TEST(StringStreamSeeking, MiddleWritesOverwriteAndEndWritesCanExtendTheSequence) {
  std::stringstream stream{"abcdef", std::ios_base::in | std::ios_base::out};

  stream.seekp(2);
  stream << "XY";
  EXPECT_EQ(stream.str(), "abXYef");

  stream.seekp(0, std::ios_base::end);
  stream << "++";
  EXPECT_EQ(stream.str(), "abXYef++");

  stream.seekg(-2, std::ios_base::end);
  std::string suffix;
  stream >> suffix;
  EXPECT_EQ(suffix, "++");

  // 写位置落在现有范围内时覆盖，不自动插入；位于末尾时扩展。定位到范围之外
  // 是否允许由 stringbuf 规则控制，失败会传播为 failbit。
}

TEST(StringBuffer, DirectStrAccessReplacesTheSequenceAndHonorsTheConfiguredMode) {
  std::stringbuf buffer{"abc", std::ios_base::in | std::ios_base::out};
  EXPECT_EQ(buffer.str(), "abc");

  buffer.str("xyz");
  EXPECT_EQ(std::char_traits<char>::to_char_type(buffer.sgetc()), 'x');
  buffer.pubseekpos(std::streampos{1}, std::ios_base::out);
  buffer.sputc('!');
  EXPECT_EQ(buffer.str(), "x!z");

  std::stringbuf input_only{"abc", std::ios_base::in};
  EXPECT_EQ(input_only.sputc('X'), std::char_traits<char>::eof());

  // stringbuf 自己不含 ios 状态位；失败直接以 traits::eof 或 streampos(-1) 返回。
  // openmode 决定是否建立 get/put 序列，不能向 input-only 缓冲区写入。
}

#if defined(__cpp_lib_stringbuf_view) && __cpp_lib_stringbuf_view >= 201803L

TEST(StringBufferView, Cxx20ViewAvoidsCopyButIsInvalidatedByBufferMutation) {
  std::ostringstream output;
  output << "payload";

  const std::string_view view = output.view();
  EXPECT_EQ(view, "payload");
  EXPECT_EQ(view.data(), output.view().data());

  output << " extended";
  EXPECT_EQ(output.view(), "payload extended");

  // view 指向 stringbuf 内部存储；任何可能重分配、str 替换、移动或析构都会使旧
  // view 悬空。本测试在修改后重新获取 view，不读取先前地址。
}

#else

TEST(StringBufferView, LockedLibraryGapRecordsTheCxx20NonOwningObserver) {
  GTEST_SKIP() << "The locked library does not expose C++20 basic_stringbuf::view";
}

#endif

TEST(StringStreamMove, RvalueStrCanMoveOutTheSequenceAndSetterAcceptsAnRvalueString) {
  std::ostringstream output;
  output << std::string(200, 'x');

  std::string moved = std::move(output).str();
  EXPECT_EQ(moved.size(), 200U);
  EXPECT_EQ(moved.front(), 'x');

  std::string replacement{"new sequence"};
  std::istringstream input;
  input.str(std::move(replacement));
  std::string first;
  input >> first;
  EXPECT_EQ(first, "new");

  // C++20 为 str 增加右值路径，可转移大缓冲区；移动后的流/源 string 仍有效但
  // 内容未指定，只能重新赋值或析构，不能断言它一定为空。
}

TEST(StringStreamMove, MovingAStreamTransfersItsInternalBufferAndLeavesAValidSource) {
  std::stringstream source;
  source << "42";
  std::stringstream destination{std::move(source)};

  int value = 0;
  destination >> value;
  EXPECT_EQ(value, 42);

  source = std::stringstream{};
  source << "reused";
  EXPECT_EQ(source.str(), "reused");

  std::stringstream other;
  other << "other";
  destination.swap(other);
  EXPECT_EQ(destination.str(), "other");

  // 移动/交换 stringstream 时，其 basic_ios 会重新关联各自内部 stringbuf；不能
  // 保存旧 rdbuf 指针跨操作使用。移动源可赋新值后复用。
}

TEST(WideStringStreams, WideAliasesUseWcharTraitsAndPreserveWideCodeUnits) {
  std::wostringstream output;
  output << L"value=" << 42;
  EXPECT_EQ(output.str(), L"value=42");

  std::wistringstream input{L"17"};
  int value = 0;
  input >> value;
  EXPECT_EQ(value, 17);

  static_assert(std::is_same_v<std::wstringstream::char_type, wchar_t>);

  // 宽流与窄流共享状态/缓冲协议，只把 CharT/traits/facet 换成 wchar_t 版本；
  // 它仍不自动把任意窄字符串转成 Unicode，也受 locale 转码规则约束。
}

}  // namespace
