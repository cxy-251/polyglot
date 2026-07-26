// polyglot-covers:
// - cpp.stdlib.filesystem.create-directory-versus-create-directories-return
// - cpp.stdlib.filesystem.create-directory-copying-attributes
// - cpp.stdlib.filesystem.copy-file-skip-existing-and-overwrite-existing
// - cpp.stdlib.filesystem.copy-recursive-directory-tree
// - cpp.stdlib.filesystem.rename-and-remove-workflow
// - cpp.stdlib.filesystem.remove-all-count-and-idempotent-cleanup
// - cpp.stdlib.filesystem.copy-error-code-and-invalid-option-trap
// - cpp.stdlib.filesystem.absolute-current-path-and-temp-directory-query
// - cpp.stdlib.filesystem.operation-race-and-partial-effect-traps

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <string_view>
#include <system_error>

namespace {

namespace fs = std::filesystem;

class FilesystemOperationsTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    root_ = fs::temp_directory_path() /
            (std::string{"polyglot-cpp-fs-ops-"} + info->name());
    std::error_code error;
    fs::remove_all(root_, error);
    ASSERT_TRUE(fs::create_directory(root_));
  }

  void TearDown() override {
    std::error_code error;
    fs::remove_all(root_, error);
  }

  static void write_file(const fs::path& path, std::string_view text) {
    std::ofstream output{path, std::ios_base::binary};
    ASSERT_TRUE(output.is_open());
    output.write(text.data(), static_cast<std::streamsize>(text.size()));
    ASSERT_TRUE(output.good());
  }

  static std::string read_file(const fs::path& path) {
    std::ifstream input{path, std::ios_base::binary};
    return {std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
  }

  fs::path root_;
};

TEST_F(
    FilesystemOperationsTest,
    CreateDirectoryReportsOneCreationAndCreateDirectoriesBuildsParents) {
  const fs::path single = root_ / "single";
  EXPECT_TRUE(fs::create_directory(single));
  EXPECT_FALSE(fs::create_directory(single));

  const fs::path nested = root_ / "a" / "b" / "c";
  EXPECT_TRUE(fs::create_directories(nested));
  EXPECT_FALSE(fs::create_directories(nested));
  EXPECT_TRUE(fs::is_directory(root_ / "a"));
  EXPECT_TRUE(fs::is_directory(nested));

  // create_directory 只创建末级且已存在目录返回 false；create_directories 递归补齐
  // 父级，只要创建过至少一级便返回 true。false 不等于错误，应结合 error_code。
}

TEST_F(FilesystemOperationsTest, CreateDirectoryCanRequestAttributesFromAnExistingDirectory) {
  const fs::path model = root_ / "model";
  const fs::path created = root_ / "created";
  ASSERT_TRUE(fs::create_directory(model));

  std::error_code error;
  fs::permissions(model, fs::perms::owner_all, fs::perm_options::replace, error);
  ASSERT_FALSE(error);
  EXPECT_TRUE(fs::create_directory(created, model));

  const auto model_owner = fs::status(model).permissions() & fs::perms::owner_all;
  const auto created_owner = fs::status(created).permissions() & fs::perms::owner_all;
  EXPECT_EQ(created_owner, model_owner);

  // create_directory(p, existing) 请求按既有目录属性创建，但实际复制哪些元数据由
  // 操作系统映射决定；它不复制目录内容，也不建立链接。
}

TEST_F(FilesystemOperationsTest, CopyFileOptionsDecideWhetherAnExistingTargetIsChanged) {
  const fs::path source = root_ / "source.txt";
  const fs::path target = root_ / "target.txt";
  write_file(source, "new");
  write_file(target, "old");

  EXPECT_FALSE(fs::copy_file(source, target, fs::copy_options::skip_existing));
  EXPECT_EQ(read_file(target), "old");

  EXPECT_TRUE(fs::copy_file(source, target, fs::copy_options::overwrite_existing));
  EXPECT_EQ(read_file(target), "new");

  std::error_code error;
  EXPECT_FALSE(fs::copy_file(source, target, fs::copy_options::none, error));
  EXPECT_TRUE(error);

  // 返回 true 表示实际复制；skip_existing 的 false 是正常分支且 ec 为空，none 遇到
  // 既有目标则失败。互斥的 existing-file 选项不能随意按位同时组合。
}

TEST_F(FilesystemOperationsTest, RecursiveCopyBuildsATreeAndPreservesFileContents) {
  const fs::path source = root_ / "source";
  const fs::path destination = root_ / "destination";
  ASSERT_TRUE(fs::create_directories(source / "nested"));
  write_file(source / "top.txt", "top");
  write_file(source / "nested" / "deep.txt", "deep");

  fs::copy(source, destination, fs::copy_options::recursive);

  EXPECT_TRUE(fs::is_directory(destination / "nested"));
  EXPECT_EQ(read_file(destination / "top.txt"), "top");
  EXPECT_EQ(read_file(destination / "nested" / "deep.txt"), "deep");

  // copy_options::recursive 明确递归目录；一次失败前可能已产生部分目标树，没有事务
  // 回滚保证。关键部署应先复制到临时目录，完整验证后再原子 rename。
}

TEST_F(FilesystemOperationsTest, RenameMovesANameAndRemoveHandlesFilesAndEmptyDirectories) {
  const fs::path source = root_ / "before.txt";
  const fs::path destination = root_ / "after.txt";
  write_file(source, "content");

  fs::rename(source, destination);
  EXPECT_FALSE(fs::exists(source));
  EXPECT_EQ(read_file(destination), "content");

  EXPECT_TRUE(fs::remove(destination));
  EXPECT_FALSE(fs::remove(destination));

  const fs::path empty = root_ / "empty";
  ASSERT_TRUE(fs::create_directory(empty));
  EXPECT_TRUE(fs::remove(empty));

  const fs::path nonempty = root_ / "nonempty";
  ASSERT_TRUE(fs::create_directory(nonempty));
  write_file(nonempty / "child", "x");
  std::error_code error;
  EXPECT_FALSE(fs::remove(nonempty, error));
  EXPECT_TRUE(error);

  // remove 只删文件或空目录；不存在返回 false 且不算错误。rename 的跨文件系统、
  // 覆盖既有目标和原子性由平台约束，不能当通用事务 API。
}

TEST_F(FilesystemOperationsTest, RemoveAllReturnsTheNumberOfRemovedFilesystemObjects) {
  const fs::path tree = root_ / "tree";
  ASSERT_TRUE(fs::create_directories(tree / "a" / "b"));
  write_file(tree / "one", "1");
  write_file(tree / "a" / "two", "2");

  const auto removed = fs::remove_all(tree);
  EXPECT_GE(removed, 5U);
  EXPECT_FALSE(fs::exists(tree));
  EXPECT_EQ(fs::remove_all(tree), 0U);

  // 返回数量包含目录和文件，具体树中若有实现对象可能不同；清理不存在路径返回 0，
  // 因而 fixture 可幂等调用。对不可信路径使用 remove_all 前必须验证安全根边界。
}

TEST_F(FilesystemOperationsTest, ErrorCodeWorkflowKeepsExpectedFailuresOutOfExceptionControlFlow) {
  const fs::path missing = root_ / "missing";
  const fs::path target = root_ / "target";
  std::error_code error;

  fs::copy(missing, target, fs::copy_options::recursive, error);
  EXPECT_TRUE(error);
  EXPECT_FALSE(fs::exists(target));

  error = std::make_error_code(std::errc::permission_denied);
  EXPECT_FALSE(fs::create_directory(root_, error));
  EXPECT_FALSE(error);

  // error_code 重载为预期失败提供显式分支，成功/“已存在”会清除旧 ec。它仍可能
  // 已产生部分副作用，不能把“不抛异常”误解成原子操作。
}

TEST(FilesystemQueries, AbsoluteUsesCurrentPathWithoutChangingItAndTempPathIsAbsolute) {
  const fs::path before = fs::current_path();
  const fs::path absolute = fs::absolute("relative-name");
  const fs::path temporary = fs::temp_directory_path();

  EXPECT_TRUE(absolute.is_absolute());
  EXPECT_EQ(absolute.filename(), "relative-name");
  EXPECT_EQ(fs::current_path(), before);
  EXPECT_TRUE(temporary.is_absolute());
  EXPECT_TRUE(fs::is_directory(temporary));

  // absolute 通常以 current_path 为基准但不规范化 '..' 或解析链接；current_path
  // 是进程全局可变状态，库和并发测试应查询/传参，而不要临时切换工作目录。
}

}  // namespace
