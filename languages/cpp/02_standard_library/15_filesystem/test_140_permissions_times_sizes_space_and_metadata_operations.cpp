// polyglot-covers:
// - cpp.stdlib.filesystem.resize-file-shrink-grow-and-content-boundary
// - cpp.stdlib.filesystem.last-write-time-get-set-and-filesystem-clock
// - cpp.stdlib.filesystem.permissions-replace-add-remove-and-options
// - cpp.stdlib.filesystem.space-info-capacity-free-and-available
// - cpp.stdlib.filesystem.hard-link-count-and-error-sentinel
// - cpp.stdlib.filesystem.is-empty-file-and-directory
// - cpp.stdlib.filesystem.metadata-error-code-sentinels
// - cpp.stdlib.filesystem.metadata-race-rounding-and-platform-traps

#include <gtest/gtest.h>

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <string_view>
#include <system_error>

namespace {

namespace fs = std::filesystem;
using namespace std::chrono_literals;

class FilesystemMetadataTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    root_ = fs::temp_directory_path() /
            (std::string{"polyglot-cpp-fs-meta-"} + info->name());
    std::error_code error;
    fs::remove_all(root_, error);
    ASSERT_TRUE(fs::create_directories(root_ / "empty-directory"));
    file_ = root_ / "file.txt";
    write("payload");
  }

  void TearDown() override {
    std::error_code error;
    fs::remove_all(root_, error);
  }

  void write(std::string_view text) const {
    std::ofstream output{file_, std::ios_base::binary};
    ASSERT_TRUE(output.is_open());
    output.write(text.data(), static_cast<std::streamsize>(text.size()));
    ASSERT_TRUE(output.good());
  }

  std::string read() const {
    std::ifstream input{file_, std::ios_base::binary};
    return {std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
  }

  fs::path root_;
  fs::path file_;
};

TEST_F(FilesystemMetadataTest, ResizeFileTruncatesOrExtendsWhilePreservingTheOldPrefix) {
  EXPECT_EQ(fs::file_size(file_), 7U);

  fs::resize_file(file_, 3);
  EXPECT_EQ(fs::file_size(file_), 3U);
  EXPECT_EQ(read(), "pay");

  fs::resize_file(file_, 10);
  EXPECT_EQ(fs::file_size(file_), 10U);
  const std::string extended = read();
  ASSERT_EQ(extended.size(), 10U);
  EXPECT_EQ(extended.substr(0, 3), "pay");

  // 缩小丢弃尾部；扩大保留原前缀，但新增区域的值由文件系统语义决定，标准接口
  // 不应被当作高级结构的安全初始化。操作也不提供原子替换保证。
}

TEST_F(FilesystemMetadataTest, LastWriteTimeUsesFileClockAndMayRoundToFilesystemResolution) {
  const auto original = fs::last_write_time(file_);
  const auto requested = original - 60s;
  fs::last_write_time(file_, requested);
  const auto observed = fs::last_write_time(file_);

  const auto difference = observed > requested ? observed - requested : requested - observed;
  EXPECT_LE(difference, 1s);

  // file_time_type 使用 filesystem clock，不保证与 system_clock 同 epoch。设置值可能
  // 按文件系统时间分辨率舍入，所以测试允许小误差而不比较内部 tick 数。
}

TEST_F(FilesystemMetadataTest, PermissionsCanReplaceAddAndRemoveSelectedPortableBits) {
  std::error_code error;
  fs::permissions(
      file_,
      fs::perms::owner_read | fs::perms::owner_write,
      fs::perm_options::replace,
      error);
  ASSERT_FALSE(error);

  auto owner = fs::status(file_).permissions() & fs::perms::owner_all;
  EXPECT_EQ(owner, fs::perms::owner_read | fs::perms::owner_write);

  fs::permissions(file_, fs::perms::owner_exec, fs::perm_options::add, error);
  ASSERT_FALSE(error);
  owner = fs::status(file_).permissions() & fs::perms::owner_all;
  EXPECT_NE(owner & fs::perms::owner_exec, fs::perms::none);

  fs::permissions(file_, fs::perms::owner_exec, fs::perm_options::remove, error);
  ASSERT_FALSE(error);
  owner = fs::status(file_).permissions() & fs::perms::owner_all;
  EXPECT_EQ(owner & fs::perms::owner_exec, fs::perms::none);

  // replace/add/remove 三者必须恰选一种；nofollow 决定是否作用于符号链接自身。
  // ACL、umask 与平台只读属性可能让可观察结果比 POSIX 九个位更复杂。
}

TEST(FilesystemSpace, CapacityFreeAndAvailableDescribeDifferentStorageLimits) {
  std::error_code error;
  const fs::space_info info = fs::space(fs::temp_directory_path(), error);
  ASSERT_FALSE(error);

  EXPECT_NE(info.capacity, static_cast<std::uintmax_t>(-1));
  EXPECT_NE(info.free, static_cast<std::uintmax_t>(-1));
  EXPECT_NE(info.available, static_cast<std::uintmax_t>(-1));
  EXPECT_GE(info.capacity, info.free);
  EXPECT_GE(info.free, info.available);

  // free 是文件系统未分配空间，available 是当前调用者可用空间，可能因保留块更小。
  // 数值是瞬时快照，不能先查询后假定后续大文件写入一定成功。
}

TEST_F(FilesystemMetadataTest, HardLinkCountIsAtLeastOneAndFailureUsesUintmaxSentinel) {
  EXPECT_GE(fs::hard_link_count(file_), 1U);

  std::error_code error;
  const auto missing_count = fs::hard_link_count(root_ / "missing", error);
  EXPECT_TRUE(error);
  EXPECT_EQ(missing_count, static_cast<std::uintmax_t>(-1));

  // 链接数可能因其他进程并发创建/删除而变化；缺失时返回 uintmax_t(-1) 并设置 ec，
  // 不能把巨大哨兵误当真实计数。
}

TEST_F(FilesystemMetadataTest, IsEmptyUsesSizeForFilesAndEntriesForDirectories) {
  EXPECT_FALSE(fs::is_empty(file_));
  EXPECT_TRUE(fs::is_empty(root_ / "empty-directory"));

  write("");
  EXPECT_TRUE(fs::is_empty(file_));

  std::ofstream{root_ / "empty-directory" / "child"} << 'x';
  EXPECT_FALSE(fs::is_empty(root_ / "empty-directory"));

  // 对文件，empty 表示 size==0；对目录，表示没有目录项。它不读取文件内容，也不
  // 把只含空白的文本当空。
}

TEST_F(FilesystemMetadataTest, MetadataErrorCodeOverloadsReturnDocumentedMinimumSentinels) {
  const fs::path missing = root_ / "missing";
  std::error_code error;

  const auto time = fs::last_write_time(missing, error);
  EXPECT_TRUE(error);
  EXPECT_EQ(time, fs::file_time_type::min());

  error.clear();
  const auto info = fs::space(missing, error);
  EXPECT_TRUE(error);
  EXPECT_EQ(info.capacity, static_cast<std::uintmax_t>(-1));
  EXPECT_EQ(info.free, static_cast<std::uintmax_t>(-1));
  EXPECT_EQ(info.available, static_cast<std::uintmax_t>(-1));

  // 每个查询有自己的失败哨兵：time 用 min，空间字段用 uintmax_t(-1)。所有哨兵
  // 都可能看似普通值，必须以 ec 为主判断成功。
}

}  // namespace
