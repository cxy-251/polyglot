// polyglot-covers:
// - cpp.stdlib.filesystem.file-status-type-permissions-and-status-known
// - cpp.stdlib.filesystem.status-predicates-regular-directory-and-missing
// - cpp.stdlib.filesystem.throwing-versus-error-code-overloads
// - cpp.stdlib.filesystem.filesystem-error-code-path1-path2-and-what
// - cpp.stdlib.filesystem.directory-entry-observers-refresh-and-replace-filename
// - cpp.stdlib.filesystem.file-size-and-is-empty
// - cpp.stdlib.filesystem.perms-bitmask-and-unknown-sentinel
// - cpp.stdlib.filesystem.race-between-query-and-use-trap

#include <gtest/gtest.h>

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <system_error>

namespace {

namespace fs = std::filesystem;

class FilesystemStatusTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    root_ = fs::temp_directory_path() /
            (std::string{"polyglot-cpp-fs-status-"} + info->name());
    std::error_code error;
    fs::remove_all(root_, error);
    ASSERT_TRUE(fs::create_directories(root_ / "directory"));
    file_ = root_ / "file.txt";
    std::ofstream output{file_, std::ios_base::binary};
    ASSERT_TRUE(output.is_open());
    output << "payload";
    output.close();
    ASSERT_TRUE(output.good());
  }

  void TearDown() override {
    std::error_code error;
    fs::remove_all(root_, error);
  }

  fs::path root_;
  fs::path file_;
};

TEST_F(FilesystemStatusTest, FileStatusCombinesATypeAndPermissionBitmask) {
  const fs::file_status file_status = fs::status(file_);
  const fs::file_status directory_status = fs::status(root_ / "directory");
  const fs::file_status missing_status = fs::status(root_ / "missing");

  EXPECT_TRUE(fs::status_known(file_status));
  EXPECT_TRUE(fs::is_regular_file(file_status));
  EXPECT_FALSE(fs::is_directory(file_status));
  EXPECT_TRUE(fs::is_directory(directory_status));
  EXPECT_EQ(missing_status.type(), fs::file_type::not_found);
  EXPECT_TRUE(fs::status_known(missing_status));
  EXPECT_FALSE(fs::exists(missing_status));
  EXPECT_NE(file_status.permissions(), fs::perms::unknown);

  // not_found 是已知状态，所以 status_known 为真但 exists 为假；file_type::none 才
  // 表示尚未取得状态。权限是位掩码快照，随后文件系统可能已经变化。
}

TEST(FilesystemStatusValue, ObserversAndModifiersCanRepresentSyntheticMetadata) {
  fs::file_status status{
      fs::file_type::regular,
      fs::perms::owner_read | fs::perms::owner_write};

  EXPECT_EQ(status.type(), fs::file_type::regular);
  EXPECT_EQ(
      status.permissions() & fs::perms::owner_all,
      fs::perms::owner_read | fs::perms::owner_write);

  status.type(fs::file_type::directory);
  status.permissions(fs::perms::owner_all);
  EXPECT_TRUE(fs::is_directory(status));
  EXPECT_EQ(status.permissions() & fs::perms::owner_all, fs::perms::owner_all);

  // file_status 是普通值对象；修改它不会 chmod 或改变真实文件，只适合传递一次
  // 查询结果或构造测试输入。
}

TEST_F(FilesystemStatusTest, ErrorCodeOverloadsClearOnSuccessAndReturnSentinelsOnFailure) {
  std::error_code error = std::make_error_code(std::errc::permission_denied);
  const auto size = fs::file_size(file_, error);
  EXPECT_FALSE(error);
  EXPECT_EQ(size, 7U);

  const auto failed_size = fs::file_size(root_ / "missing", error);
  EXPECT_TRUE(error);
  EXPECT_EQ(failed_size, static_cast<std::uintmax_t>(-1));

  const auto missing = fs::status(root_ / "missing", error);
  EXPECT_TRUE(error);
  EXPECT_EQ(missing.type(), fs::file_type::not_found);
  EXPECT_EQ(fs::status(root_ / "missing").type(), fs::file_type::not_found);

  // error_code 重载成功时 clear(ec)，底层 stat 的 ENOENT 则保留在 ec 并返回
  // not_found。抛异常 status 仍把 not_found 当可用结果；file_size 则返回 -1+ec。
}

TEST_F(FilesystemStatusTest, ThrowingOverloadsCarryOperationAndPathsInFilesystemError) {
  const fs::path missing = root_ / "missing";

  try {
    (void)fs::file_size(missing);
    FAIL() << "file_size of a missing path must fail";
  } catch (const fs::filesystem_error& error) {
    EXPECT_TRUE(error.code());
    EXPECT_EQ(error.path1(), missing);
    EXPECT_TRUE(error.path2().empty());
    EXPECT_NE(std::string{error.what()}.find("missing"), std::string::npos);
  }

  const fs::path destination = root_ / "destination";
  const fs::filesystem_error manual{
      "copy",
      file_,
      destination,
      std::make_error_code(std::errc::permission_denied)};
  EXPECT_EQ(manual.path1(), file_);
  EXPECT_EQ(manual.path2(), destination);
  EXPECT_EQ(manual.code(), std::make_error_code(std::errc::permission_denied));

  // 抛异常重载适合失败即终止的工作流；filesystem_error 可保存一条或两条路径与
  // error_code。what 文本由实现决定，只应查码与 path 访问器。
}

TEST_F(FilesystemStatusTest, DirectoryEntryStoresAPathAndCanRefreshItsObservedMetadata) {
  fs::directory_entry entry{file_};
  EXPECT_EQ(entry.path(), file_);
  EXPECT_TRUE(entry.exists());
  EXPECT_TRUE(entry.is_regular_file());
  EXPECT_EQ(entry.file_size(), 7U);

  ASSERT_TRUE(fs::remove(file_));
  std::error_code error;
  entry.refresh(error);
  EXPECT_FALSE(entry.exists());

  entry.assign(root_ / "directory", error);
  ASSERT_FALSE(error);
  EXPECT_TRUE(entry.is_directory());
  entry.replace_filename("missing", error);
  EXPECT_EQ(entry.path(), root_ / "missing");
  EXPECT_FALSE(entry.exists());

  // directory_entry 同时保存 path 与实现允许缓存的属性；外部变化后显式 refresh。
  // replace_filename 会更新路径并刷新状态，但仍不创建、移动或重命名磁盘对象。
}

TEST_F(FilesystemStatusTest, FileSizeAndIsEmptyHaveTypeSpecificContracts) {
  EXPECT_EQ(fs::file_size(file_), 7U);
  EXPECT_FALSE(fs::is_empty(file_));
  EXPECT_TRUE(fs::is_empty(root_ / "directory"));

  std::ofstream{root_ / "directory" / "child.txt"} << "x";
  EXPECT_FALSE(fs::is_empty(root_ / "directory"));

  std::error_code error;
  const auto directory_size = fs::file_size(root_ / "directory", error);
  EXPECT_TRUE(error);
  EXPECT_EQ(directory_size, static_cast<std::uintmax_t>(-1));

  // is_empty 对普通文件看 size，对目录看是否含条目；file_size 只承诺普通文件。
  // 先 exists 再打开仍有竞态，安全代码应直接执行目标操作并处理最终错误。
}

TEST(FilesystemPermissions, BitmaskOperatorsComposePortableClassesButNotPlatformAclDetails) {
  constexpr auto owner_rw = fs::perms::owner_read | fs::perms::owner_write;
  constexpr auto public_read = fs::perms::group_read | fs::perms::others_read;
  constexpr auto mode = owner_rw | public_read;

  static_assert((mode & fs::perms::owner_read) != fs::perms::none);
  static_assert((mode & fs::perms::owner_exec) == fs::perms::none);
  EXPECT_NE(mode, fs::perms::unknown);

  // perms 模拟 POSIX 权限位，但 ACL、继承、只读属性等平台机制不一定完整映射。
  // unknown 是查询不可得的哨兵，不应参与“允许访问”的默认决策。
}

}  // namespace
