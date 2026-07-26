// polyglot-covers:
// - cpp.stdlib.io.file-stream-path-open-close-is-open-and-truncation
// - cpp.stdlib.io.file-stream-app-versus-ate-and-seeking
// - cpp.stdlib.io.file-stream-binary-raw-byte-round-trip
// - cpp.stdlib.io.file-stream-get-put-position-and-overwrite
// - cpp.stdlib.io.file-stream-open-failure-state-and-exceptions
// - cpp.stdlib.io.file-stream-close-reopen-and-flush
// - cpp.stdlib.io.filebuf-open-sputn-seek-sgetn-and-close
// - cpp.stdlib.io.file-stream-move-ownership-and-moved-from-reuse
// - cpp.stdlib.io.file-stream-temporary-path-and-cleanup-workflow

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <ios>
#include <iterator>
#include <string>
#include <system_error>
#include <utility>

namespace {

class FileStreamTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    path_ = std::filesystem::temp_directory_path() /
            (std::string{"polyglot-cpp-fstream-"} + info->name() + ".tmp");
    std::error_code error;
    std::filesystem::remove(path_, error);
  }

  void TearDown() override {
    std::error_code error;
    std::filesystem::remove(path_, error);
  }

  void write_text(std::string_view text) const {
    std::ofstream output{path_, std::ios_base::out | std::ios_base::trunc};
    ASSERT_TRUE(output.is_open());
    output.write(text.data(), static_cast<std::streamsize>(text.size()));
    ASSERT_TRUE(output.good());
  }

  std::string read_text() const {
    std::ifstream input{path_, std::ios_base::in | std::ios_base::binary};
    return {std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
  }

  std::filesystem::path path_;
};

TEST_F(FileStreamTest, DefaultOfstreamTruncatesAndIfstreamReadsThroughAPathObject) {
  write_text("old content");

  std::ofstream output{path_};
  ASSERT_TRUE(output.is_open());
  output << "new" << '\n';
  output.close();
  EXPECT_FALSE(output.is_open());
  EXPECT_TRUE(output.good());

  std::ifstream input{path_};
  std::string line;
  ASSERT_TRUE(static_cast<bool>(std::getline(input, line)));
  EXPECT_EQ(line, "new");

  // ofstream 默认模式含 out；对普通文件它还隐含 trunc，旧内容会在打开时丢失。
  // C++17 起文件流直接接收 filesystem::path，不需要临时窄化平台原生路径。
}

TEST_F(FileStreamTest, FileAppForcesEveryWriteToEndWhileAteOnlyChoosesInitialPosition) {
  write_text("seed");
  {
    std::ofstream appending{path_, std::ios_base::out | std::ios_base::app};
    ASSERT_TRUE(appending.is_open());
    appending.seekp(0);
    appending << 'X';
  }
  EXPECT_EQ(read_text(), "seedX");

  write_text("seed");
  {
    std::fstream at_end{
        path_, std::ios_base::in | std::ios_base::out | std::ios_base::ate};
    ASSERT_TRUE(at_end.is_open());
    at_end.seekp(0);
    at_end << 'Y';
  }
  EXPECT_EQ(read_text(), "Yeed");

  // filebuf 的 app 要求每次写前定位末尾，seekp 不能把下一次写留在开头；ate 只
  // 决定打开后的初始位置。加入 in 可避免 out 单独打开时隐含 trunc。
}

TEST_F(FileStreamTest, BinaryModeRoundTripsRawBytesIncludingNullAndNewline) {
  const std::array<unsigned char, 6> bytes{0x00, 0x0A, 0x0D, 0x7F, 0x80, 0xFF};
  {
    std::ofstream output{path_, std::ios_base::out | std::ios_base::binary};
    ASSERT_TRUE(output.is_open());
    output.write(
        reinterpret_cast<const char*>(bytes.data()),
        static_cast<std::streamsize>(bytes.size()));
    ASSERT_TRUE(output.good());
  }

  std::array<unsigned char, 6> restored{};
  std::ifstream input{path_, std::ios_base::in | std::ios_base::binary};
  input.read(
      reinterpret_cast<char*>(restored.data()),
      static_cast<std::streamsize>(restored.size()));

  EXPECT_EQ(input.gcount(), static_cast<std::streamsize>(restored.size()));
  EXPECT_EQ(restored, bytes);

  // binary 关闭实现可能进行的换行/文件尾转换；它不定义对象序列化格式。直接写
  // 整数对象仍会带入字节序、宽度、填充和表示差异，应自行规定编码。
}

TEST_F(FileStreamTest, ExplicitSeeksCoordinateReadingAndWritingInACombinedFstream) {
  write_text("0123456789");
  std::fstream stream{
      path_, std::ios_base::in | std::ios_base::out | std::ios_base::binary};
  ASSERT_TRUE(stream.is_open());

  stream.seekg(3);
  char value = '\0';
  stream.get(value);
  EXPECT_EQ(value, '3');
  EXPECT_EQ(stream.tellg(), std::streampos{4});

  stream.seekp(5);
  stream.write("XY", 2);
  stream.flush();
  EXPECT_EQ(stream.tellp(), std::streampos{7});

  stream.seekg(0);
  std::string contents(10, '\0');
  stream.read(contents.data(), static_cast<std::streamsize>(contents.size()));
  EXPECT_EQ(contents, "01234XY789");

  // 混合读写时在方向切换处显式 seek/flush，避免依赖 filebuf 的联合文件位置和
  // 缓冲时机。tellg/tellp 返回逻辑 streampos，不应假设总等于物理字节偏移。
}

TEST_F(FileStreamTest, OpenFailureSetsStateAndExceptionMasksCanThrowImmediately) {
  const auto missing = path_.parent_path() / "polyglot-cpp-missing-dir" / "file.txt";
  std::ifstream input{missing};

  EXPECT_FALSE(input.is_open());
  EXPECT_TRUE(input.fail());
  EXPECT_THROW(input.exceptions(std::ios_base::failbit), std::ios_base::failure);

  input.exceptions(std::ios_base::goodbit);
  input.clear();
  EXPECT_TRUE(input.good());

  std::ifstream throwing;
  throwing.exceptions(std::ios_base::failbit | std::ios_base::badbit);
  EXPECT_THROW(throwing.open(missing), std::ios_base::failure);
  EXPECT_TRUE(throwing.fail());

  // 构造/打开失败默认不抛，只置 failbit。给已有失败状态安装相交的 exceptions
  // 掩码会当场抛；异常后的流仍保留错误位，恢复顺序与普通流相同。
}

TEST_F(FileStreamTest, AClosedStreamCanBeClearedAndReopenedForAnotherSession) {
  std::ofstream output;
  output.open(path_);
  ASSERT_TRUE(output.is_open());
  output << "first";
  output.flush();
  EXPECT_TRUE(output.good());
  output.close();
  EXPECT_FALSE(output.is_open());

  output.open(path_, std::ios_base::out | std::ios_base::app);
  ASSERT_TRUE(output.is_open());
  output << "+second";
  output.close();

  EXPECT_EQ(read_text(), "first+second");

  // close 负责提交缓冲并解除文件关联；失败会反映到流状态。成功关闭后可 reopen，
  // 但若上次会话留下 failbit，仍需 clear 后新会话才能正常 I/O。
}

TEST_F(FileStreamTest, FilebufExposesOpenTransferPositionAndCloseWithoutIosState) {
  std::filebuf buffer;
  ASSERT_EQ(
      buffer.open(path_, std::ios_base::out | std::ios_base::trunc | std::ios_base::binary),
      &buffer);
  EXPECT_TRUE(buffer.is_open());
  EXPECT_EQ(buffer.sputn("abcdef", 6), 6);
  EXPECT_NE(buffer.pubsync(), -1);
  EXPECT_EQ(buffer.close(), &buffer);

  ASSERT_EQ(buffer.open(path_, std::ios_base::in | std::ios_base::binary), &buffer);
  EXPECT_EQ(
      buffer.pubseekpos(std::streampos{2}, std::ios_base::in),
      std::streampos{2});
  std::array<char, 3> text{};
  EXPECT_EQ(buffer.sgetn(text.data(), text.size()), 3);
  EXPECT_EQ(std::string(text.data(), text.size()), "cde");
  EXPECT_EQ(buffer.close(), &buffer);

  // filebuf 直接以空指针、EOF、-1 位置等返回失败，没有 rdstate/exceptions。
  // file stream 在它外面把这些低层结果转换成统一的 ios 状态机。
}

TEST_F(FileStreamTest, MovingAFileStreamTransfersExclusiveAssociationAndSourceCanBeReused) {
  std::ofstream source{path_};
  ASSERT_TRUE(source.is_open());
  source << "before";

  std::ofstream destination{std::move(source)};
  EXPECT_TRUE(destination.is_open());
  EXPECT_FALSE(source.is_open());
  destination << "+after";
  destination.close();

  EXPECT_EQ(read_text(), "before+after");

  source = std::ofstream{path_, std::ios_base::out | std::ios_base::app};
  ASSERT_TRUE(source.is_open());
  source << "+reused";
  source.close();
  EXPECT_EQ(read_text(), "before+after+reused");

  // 文件关联是独占资源，移动后由目标负责 flush/close；源不再打开但仍可赋新流。
  // 不要把移动前取得的 rdbuf 指针或 native 句柄当作稳定所有权引用。
}

}  // namespace
