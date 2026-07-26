// polyglot-covers:
// - cpp.stdlib.io.cstdio-fopen-modes-fclose-fflush-and-raii
// - cpp.stdlib.io.cstdio-fputs-fgets-fgetc-fputc-and-null-termination
// - cpp.stdlib.io.cstdio-feof-ferror-clearerr-and-ungetc
// - cpp.stdlib.io.cstdio-fread-fwrite-item-count-and-binary-data
// - cpp.stdlib.io.cstdio-fseek-ftell-fgetpos-fsetpos-and-rewind
// - cpp.stdlib.io.cstdio-snprintf-required-size-truncation-and-terminator
// - cpp.stdlib.io.cstdio-sscanf-assignment-count-width-scanset-and-percent-n
// - cpp.stdlib.io.cstdio-tmpfile-and-automatic-removal
// - cpp.stdlib.io.cstdio-setvbuf-buffer-lifetime
// - cpp.stdlib.io.cstdio-rename-remove-and-error-reporting
// - cpp.stdlib.io.cinttypes-intmax-conversion-format-macros-and-division

#include <gtest/gtest.h>

#include <array>
#include <cerrno>
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <memory>
#include <string>
#include <string_view>
#include <system_error>

namespace {

struct FileCloser {
  void operator()(std::FILE* file) const {
    if (file != nullptr) {
      std::fclose(file);
    }
  }
};

using FileHandle = std::unique_ptr<std::FILE, FileCloser>;

class CStdioTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    const std::string stem = std::string{"polyglot-cpp-cstdio-"} + info->name();
    path_ = std::filesystem::temp_directory_path() / (stem + ".tmp");
    renamed_path_ = std::filesystem::temp_directory_path() / (stem + "-renamed.tmp");
    cleanup();
  }

  void TearDown() override { cleanup(); }

  void cleanup() {
    std::error_code error;
    std::filesystem::remove(path_, error);
    error.clear();
    std::filesystem::remove(renamed_path_, error);
  }

  FileHandle open(const char* mode) const {
    return FileHandle{std::fopen(path_.string().c_str(), mode)};
  }

  std::filesystem::path path_;
  std::filesystem::path renamed_path_;
};

TEST_F(CStdioTest, TextFunctionsWriteFlushAndReadNullTerminatedLines) {
  {
    auto output = open("w");
    ASSERT_NE(output, nullptr);
    EXPECT_GE(std::fputs("alpha", output.get()), 0);
    EXPECT_EQ(std::fputc('\n', output.get()), '\n');
    EXPECT_EQ(std::fprintf(output.get(), "%s=%d\n", "count", 3), 8);
    EXPECT_EQ(std::fflush(output.get()), 0);
    EXPECT_EQ(std::ftell(output.get()), 14L);
  }

  auto input = open("r");
  ASSERT_NE(input, nullptr);
  std::array<char, 16> line{};
  ASSERT_EQ(std::fgets(line.data(), line.size(), input.get()), line.data());
  EXPECT_STREQ(line.data(), "alpha\n");

  std::array<char, 8> name{};
  int count = 0;
  EXPECT_EQ(std::fscanf(input.get(), "%7[^=]=%d", name.data(), &count), 2);
  EXPECT_STREQ(name.data(), "count");
  EXPECT_EQ(count, 3);

  // fputs 不自动写换行；fgets 最多读 n-1 个字符并补零，若读到换行会保留它。
  // FILE* 需要确定性 fclose；用带 deleter 的 unique_ptr 可让异常/断言路径也释放。
}

TEST_F(CStdioTest, EofIsRecordedOnlyAfterAReadAttemptsPastTheEndAndUngetcClearsIt) {
  {
    auto output = open("w");
    ASSERT_NE(output, nullptr);
    ASSERT_GE(std::fputs("ab", output.get()), 0);
  }

  auto input = open("r");
  ASSERT_NE(input, nullptr);
  EXPECT_EQ(std::fgetc(input.get()), 'a');
  EXPECT_EQ(std::fgetc(input.get()), 'b');
  EXPECT_EQ(std::feof(input.get()), 0);

  EXPECT_EQ(std::fgetc(input.get()), EOF);
  EXPECT_NE(std::feof(input.get()), 0);
  EXPECT_EQ(std::ferror(input.get()), 0);

  std::clearerr(input.get());
  EXPECT_EQ(std::feof(input.get()), 0);
  EXPECT_EQ(std::ungetc('Z', input.get()), 'Z');
  EXPECT_EQ(std::fgetc(input.get()), 'Z');
  EXPECT_EQ(std::fgetc(input.get()), EOF);

  // 文件位置到末尾本身不设置 EOF 指示器；必须有读取失败。ungetc 成功会清 EOF，
  // 但标准只保证至少一个字符的回推容量，也不能用它任意改写文件。
}

TEST_F(CStdioTest, BinaryFunctionsReturnCompleteItemCountsNotRawByteCounts) {
  const std::array<unsigned char, 6> bytes{0x00, 0x01, 0x7F, 0x80, 0xFE, 0xFF};
  {
    auto output = open("wb");
    ASSERT_NE(output, nullptr);
    EXPECT_EQ(std::fwrite(bytes.data(), 2, 3, output.get()), 3U);
  }

  auto input = open("rb");
  ASSERT_NE(input, nullptr);
  std::array<unsigned char, 6> restored{};
  EXPECT_EQ(std::fread(restored.data(), 2, 3, input.get()), 3U);
  EXPECT_EQ(restored, bytes);
  EXPECT_EQ(std::fread(restored.data(), 2, 1, input.get()), 0U);
  EXPECT_NE(std::feof(input.get()), 0);

  // fread/fwrite 返回完整 item 数，不是 size*count 字节数；最后一个不完整 item
  // 不计入返回值。size 或 count 为零时不访问缓冲区并返回零。
}

TEST_F(CStdioTest, PositionFunctionsSupportOffsetsAndOpaqueSavedConversionState) {
  {
    auto output = open("wb");
    ASSERT_NE(output, nullptr);
    ASSERT_EQ(std::fwrite("abcdef", 1, 6, output.get()), 6U);
  }

  auto file = open("rb");
  ASSERT_NE(file, nullptr);
  EXPECT_EQ(std::fseek(file.get(), 2, SEEK_SET), 0);
  EXPECT_EQ(std::ftell(file.get()), 2L);

  std::fpos_t position{};
  EXPECT_EQ(std::fgetpos(file.get(), &position), 0);
  EXPECT_EQ(std::fgetc(file.get()), 'c');
  EXPECT_EQ(std::fseek(file.get(), -1, SEEK_END), 0);
  EXPECT_EQ(std::fgetc(file.get()), 'f');

  EXPECT_EQ(std::fsetpos(file.get(), &position), 0);
  EXPECT_EQ(std::fgetc(file.get()), 'c');
  std::rewind(file.get());
  EXPECT_EQ(std::ftell(file.get()), 0L);
  EXPECT_EQ(std::ferror(file.get()), 0);

  // fpos_t 可包含多字节解析状态，不应当成 long；fseek/ftell 才使用 long 偏移。
  // rewind 等价于定位开头并清除错误指示器，但没有可检查的返回值。
}

TEST(CFormattedOutput, SnprintfReportsTheUntruncatedLengthAndAlwaysTerminatesWhenSizeIsPositive) {
  std::array<char, 6> buffer{'?', '?', '?', '?', '?', '?'};

  const int required = std::snprintf(buffer.data(), buffer.size(), "%s-%d", "abc", 42);

  EXPECT_EQ(required, 6);
  EXPECT_STREQ(buffer.data(), "abc-4");
  EXPECT_EQ(buffer.back(), '\0');
  EXPECT_EQ(std::snprintf(nullptr, 0, "%#x %.2f", 255, 1.25), 9);

  // 返回值是不含终止零的完整所需长度；若 >= size，输出被截断。size>0 时末尾
  // 仍写零，因此可先用 nullptr,0 测长，再分配 required+1 并重试。
}

TEST(CFormattedInput, ScanfReturnsAssignmentsAndWidthsProtectCharacterArrays) {
  int integer = 0;
  double floating = 0.0;
  std::array<char, 6> word{};

  EXPECT_EQ(
      std::sscanf("42 3.5 token-extra", "%d %lf %5s", &integer, &floating, word.data()),
      3);
  EXPECT_EQ(integer, 42);
  EXPECT_DOUBLE_EQ(floating, 3.5);
  EXPECT_STREQ(word.data(), "token");

  std::array<char, 4> letters{};
  int digits = 0;
  int consumed = -1;
  EXPECT_EQ(
      std::sscanf("abc123tail", "%3[a-z]%d%n", letters.data(), &digits, &consumed),
      2);
  EXPECT_STREQ(letters.data(), "abc");
  EXPECT_EQ(digits, 123);
  EXPECT_EQ(consumed, 6);

  // scanf 的返回值是成功赋值数量，%n 写入消费位置但不计数。%s/%[ 不知道数组
  // 容量，必须把 width 设为 N-1；格式串与参数类型不匹配会产生未定义行为。
}

TEST(CStdioTemporaryFile, TmpfileCreatesAnAnonymousSeekableFileRemovedOnClose) {
  FileHandle file{std::tmpfile()};
  ASSERT_NE(file, nullptr);

  EXPECT_GE(std::fputs("temporary", file.get()), 0);
  std::rewind(file.get());
  std::array<char, 16> buffer{};
  EXPECT_EQ(std::fgets(buffer.data(), buffer.size(), file.get()), buffer.data());
  EXPECT_STREQ(buffer.data(), "temporary");

  // tmpfile 以二进制更新模式创建、关闭时自动删除，适合不需要路径的临时工作流。
  // 创建仍可能因权限/资源失败返回空；不要使用易竞争且不安全的 tmpnam 生成路径。
}

TEST_F(CStdioTest, SetvbufRequiresCallerStorageToOutliveTheFileAndPrecedeIo) {
  std::array<char, BUFSIZ> storage{};
  auto output = open("wb");
  ASSERT_NE(output, nullptr);

  EXPECT_EQ(std::setvbuf(output.get(), storage.data(), _IOFBF, storage.size()), 0);
  EXPECT_GE(std::fputs("buffered", output.get()), 0);
  EXPECT_EQ(std::fflush(output.get()), 0);

  // setvbuf 必须在打开后且任何其他 I/O 前调用。调用者提供的缓冲区不被 FILE
  // 拥有，必须活到 fclose；因此本例先声明 storage，后声明 RAII 文件句柄。
}

TEST_F(CStdioTest, RenameAndRemoveReportStatusWithoutThrowing) {
  {
    auto output = open("w");
    ASSERT_NE(output, nullptr);
    ASSERT_GE(std::fputs("data", output.get()), 0);
  }

  EXPECT_EQ(std::rename(path_.string().c_str(), renamed_path_.string().c_str()), 0);
  EXPECT_FALSE(std::filesystem::exists(path_));
  EXPECT_TRUE(std::filesystem::exists(renamed_path_));
  EXPECT_EQ(std::remove(renamed_path_.string().c_str()), 0);

  errno = 0;
  EXPECT_EQ(std::remove(renamed_path_.string().c_str()), -1);
  EXPECT_NE(errno, 0);

  // C 接口用 0/非零及 errno 报错，不抛异常；errno 只在失败后有意义，应在调用前
  // 清零并立即保存。rename 的跨文件系统和替换目标行为具有平台差异。
}

TEST(CInttypes, IntmaxFunctionsProvideWidestIntegerParsingFormattingAndDivision) {
  char* end = nullptr;
  const std::intmax_t value = std::strtoimax("-0x2a rest", &end, 0);
  EXPECT_EQ(value, -42);
  ASSERT_NE(end, nullptr);
  EXPECT_EQ(std::string_view(end), " rest");

  const std::imaxdiv_t division = std::imaxdiv(-17, 5);
  EXPECT_EQ(division.quot, -3);
  EXPECT_EQ(division.rem, -2);
  EXPECT_EQ(std::imaxabs(-42), 42);

  std::array<char, 64> buffer{};
  const int count = std::snprintf(buffer.data(), buffer.size(), "%" PRIdMAX, value);
  EXPECT_EQ(count, 3);
  EXPECT_STREQ(buffer.data(), "-42");

  // intmax_t/uintmax_t 是实现提供的最宽整数类型；PRI*/SCN* 宏生成匹配平台宽度
  // 的格式片段。不要把 int64_t 假定成 long 后硬写 %ld，这在不同 ABI 会错配。
}

}  // namespace
