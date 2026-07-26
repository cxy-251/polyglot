// polyglot-covers:
// - cpp.stdlib.io.ios-base-format-flags-masks-and-state-values
// - cpp.stdlib.io.basic-ios-good-eof-fail-bad-and-bool
// - cpp.stdlib.io.basic-ios-clear-setstate-and-exception-mask
// - cpp.stdlib.io.ios-base-failure-error-code
// - cpp.stdlib.io.basic-ios-tie-fill-locale-and-rdbuf
// - cpp.stdlib.io.ios-base-xalloc-iword-and-pword
// - cpp.stdlib.io.copyfmt-copied-and-preserved-properties
// - cpp.stdlib.io.ios-base-callback-events-and-order
// - cpp.stdlib.io.fpos-streamoff-arithmetic-and-conversion-state
// - cpp.stdlib.io.openmode-and-seekdir-bitmask-types

#include <gtest/gtest.h>

#include <algorithm>
#include <cwchar>
#include <iomanip>
#include <ios>
#include <locale>
#include <sstream>
#include <string>
#include <system_error>
#include <type_traits>
#include <vector>

namespace {

struct CallbackLog {
  std::vector<std::ios_base::event> events;
};

void record_ios_event(std::ios_base::event event, std::ios_base& stream, int slot) {
  auto* log = static_cast<CallbackLog*>(stream.pword(slot));
  if (log != nullptr) {
    log->events.push_back(event);
  }
}

TEST(IosFormattingState, FlagsUseMasksWhilePrecisionAndWidthAreIndependentValues) {
  std::ostringstream output;

  const auto original = output.flags();
  output.setf(std::ios_base::hex, std::ios_base::basefield);
  output.setf(std::ios_base::showbase | std::ios_base::uppercase);
  output.precision(3);
  output.width(8);

  EXPECT_EQ(output.flags() & std::ios_base::basefield, std::ios_base::hex);
  EXPECT_NE(output.flags() & std::ios_base::showbase, std::ios_base::fmtflags{});
  EXPECT_NE(output.flags() & std::ios_base::uppercase, std::ios_base::fmtflags{});
  EXPECT_EQ(output.precision(), 3);
  EXPECT_EQ(output.width(), 8);

  output.unsetf(std::ios_base::showbase);
  EXPECT_EQ(output.flags() & std::ios_base::showbase, std::ios_base::fmtflags{});
  output.flags(original);
  EXPECT_EQ(output.flags(), original);

  // setf(flag, mask) 会先清除 mask 中旧选项，再设置新值；不用 mask 连续设置 dec/hex
  // 可能留下冲突位。width 只影响下一次特定格式化操作，precision 通常持续保留。
}

TEST(IosState, EofAloneDoesNotMakeOperatorBoolFalseButFailDoes) {
  std::istringstream input{"42"};
  int first = 0;
  int second = 7;

  input >> first;
  EXPECT_EQ(first, 42);
  EXPECT_TRUE(input.eof());
  EXPECT_FALSE(input.fail());
  EXPECT_TRUE(static_cast<bool>(input));

  input >> second;
  EXPECT_EQ(second, 7);
  EXPECT_TRUE(input.eof());
  EXPECT_TRUE(input.fail());
  EXPECT_FALSE(input.bad());
  EXPECT_FALSE(static_cast<bool>(input));
  EXPECT_TRUE(!input);

  // good 要求所有状态位都清零；operator bool 只等价于 !fail()，而 fail() 检查
  // failbit 或 badbit。一次成功读到输入末尾可只置 eofbit，读取结果仍然有效。
}

TEST(IosState, ClearReplacesAllBitsWhileSetstateAccumulatesBits) {
  std::istringstream input{"data"};

  input.setstate(std::ios_base::eofbit);
  input.setstate(std::ios_base::failbit);
  EXPECT_TRUE(input.eof());
  EXPECT_TRUE(input.fail());

  input.clear(std::ios_base::badbit);
  EXPECT_FALSE(input.eof());
  EXPECT_TRUE(input.fail());
  EXPECT_TRUE(input.bad());

  input.clear();
  EXPECT_TRUE(input.good());

  // setstate 相当于 clear(rdstate() | bits)，会累积；clear(bits) 是整体替换。
  // badbit 也会让 fail() 为真；修复格式后若只清 failbit，仍要保留有意义的其他位。
}

TEST(IosExceptions, MatchingStateBitsThrowAfterTheStateHasAlreadyBeenRecorded) {
  std::istringstream input{"not-an-int"};
  input.exceptions(std::ios_base::failbit | std::ios_base::badbit);
  int value = 99;

  try {
    input >> value;
    FAIL() << "formatted extraction must report failbit";
  } catch (const std::ios_base::failure& error) {
    EXPECT_TRUE(input.fail());
    EXPECT_EQ(value, 0);
    EXPECT_NE(error.code(), std::error_code{});
  }

  input.exceptions(std::ios_base::goodbit);
  input.clear();
  EXPECT_TRUE(input.good());

  // exceptions(mask) 不是让流停止记录状态，而是状态更新后若与 mask 相交便抛
  // ios_base::failure。恢复时先关闭异常掩码再 clear，可避免 clear 自身再次抛出。
}

TEST(BasicIosAssociations, TieFillLocaleAndBufferAreObservableStreamProperties) {
  std::istringstream input{"7"};
  std::ostringstream tied_output;

  EXPECT_EQ(input.tie(&tied_output), nullptr);
  EXPECT_EQ(input.tie(), &tied_output);
  EXPECT_EQ(input.tie(nullptr), &tied_output);

  EXPECT_EQ(tied_output.fill('*'), ' ');
  EXPECT_EQ(tied_output.fill(), '*');
  EXPECT_EQ(tied_output.getloc(), std::locale::classic());
  EXPECT_NE(tied_output.rdbuf(), nullptr);

  // 输入 sentry 会先 flush 被 tie 的输出流，常用于“先显示提示再等待输入”。
  // fill 是 basic_ios 的字符属性；locale 与 streambuf 也属于流对象而非全局设置。
}

TEST(IosExtensibleStorage, XallocCreatesProcessWideIndicesWithPerStreamValues) {
  const int integer_slot = std::ios_base::xalloc();
  const int pointer_slot = std::ios_base::xalloc();
  std::ostringstream first;
  std::ostringstream second;
  std::string metadata{"trace-id"};

  EXPECT_EQ(first.iword(integer_slot), 0L);
  EXPECT_EQ(first.pword(pointer_slot), nullptr);

  first.iword(integer_slot) = 17;
  first.pword(pointer_slot) = &metadata;

  EXPECT_EQ(first.iword(integer_slot), 17L);
  EXPECT_EQ(first.pword(pointer_slot), &metadata);
  EXPECT_EQ(second.iword(integer_slot), 0L);
  EXPECT_EQ(second.pword(pointer_slot), nullptr);

  // xalloc 的索引可由自定义 manipulator 全局缓存；iword/pword 的槽却按每个流分开。
  // pword 不拥有指针目标，插件必须自行保证寿命并用 callback 处理 copyfmt/销毁。
}

TEST(Copyfmt, ItCopiesFormattingExtensibleStorageTieLocaleAndExceptionMaskNotStateOrBuffer) {
  const int slot = std::ios_base::xalloc();
  std::ostringstream source;
  std::ostringstream destination;
  std::ostringstream tied_output;
  std::string metadata{"copied-pointer"};

  source << std::hex << std::showbase;
  source.precision(4);
  source.width(9);
  source.fill('#');
  source.tie(&tied_output);
  source.iword(slot) = 23;
  source.pword(slot) = &metadata;
  source.exceptions(std::ios_base::badbit);

  destination.setstate(std::ios_base::eofbit);
  auto* destination_buffer = destination.rdbuf();
  destination.copyfmt(source);

  EXPECT_EQ(destination.flags(), source.flags());
  EXPECT_EQ(destination.precision(), 4);
  EXPECT_EQ(destination.width(), 9);
  EXPECT_EQ(destination.fill(), '#');
  EXPECT_EQ(destination.tie(), &tied_output);
  EXPECT_EQ(destination.iword(slot), 23L);
  EXPECT_EQ(destination.pword(slot), &metadata);
  EXPECT_EQ(destination.exceptions(), std::ios_base::badbit);
  EXPECT_TRUE(destination.eof());
  EXPECT_EQ(destination.rdbuf(), destination_buffer);

  // copyfmt 专门复制“格式环境”，不复制 rdstate、rdbuf 或已读写字符。pword 只是
  // 浅复制地址；两个流不会共同拥有目标对象。
}

TEST(IosCallbacks, CopyfmtAndDestructionProduceExplicitLifecycleEvents) {
  CallbackLog log;
  {
    const int slot = std::ios_base::xalloc();
    std::ostringstream source;
    std::ostringstream destination;
    source.pword(slot) = &log;
    source.register_callback(record_ios_event, slot);

    destination.copyfmt(source);
    ASSERT_EQ(log.events.size(), 1U);
    EXPECT_EQ(log.events.front(), std::ios_base::copyfmt_event);
  }

  EXPECT_EQ(
      std::count(log.events.begin(), log.events.end(), std::ios_base::erase_event),
      2);

  // copyfmt 先对目标旧回调发 erase_event，复制源回调和存储后发 copyfmt_event；
  // 每个流析构还发 erase_event。回调不得抛异常，并按注册的逆序调用。
}

TEST(StreamPosition, FposCombinesAnOffsetWithConversionStateAndSupportsStreamoffArithmetic) {
  std::streampos position{std::streamoff{10}};
  position += std::streamoff{5};
  EXPECT_EQ(static_cast<std::streamoff>(position), std::streamoff{15});
  EXPECT_EQ(position - std::streampos{std::streamoff{3}}, std::streamoff{12});

  std::mbstate_t state{};
  position.state(state);
  auto restored = position.state();
  EXPECT_NE(std::mbsinit(&restored), 0);

  // fpos 不一定只是整数文件偏移；宽字符流还可携带多字节转换状态。需要算术时
  // 使用 streamoff，不要假定 streampos 可序列化成某个固定宽度整数。
}

TEST(IosBitmaskTypes, OpenModesComposeAndSeekDirectionsRemainDistinctTypes) {
  constexpr auto mode = std::ios_base::in | std::ios_base::out | std::ios_base::binary;
  static_assert((mode & std::ios_base::in) != std::ios_base::openmode{});
  static_assert((mode & std::ios_base::app) == std::ios_base::openmode{});
  static_assert(
      std::is_same_v<std::remove_cv_t<decltype(std::ios_base::beg)>, std::ios_base::seekdir>);

  EXPECT_NE(mode & std::ios_base::binary, std::ios_base::openmode{});

  // openmode 是可组合位掩码；seekdir 是 beg/cur/end 三种方向值，不是字节偏移。
  // 文本模式下位置与字节数可能不等价，跨平台随机访问应谨慎选择 binary。
}

}  // namespace
