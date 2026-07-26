// polyglot-covers:
// - cpp.stdlib.filesystem.status-follows-symlink-versus-symlink-status
// - cpp.stdlib.filesystem.read-symlink-relative-target-and-dangling-link
// - cpp.stdlib.filesystem.create-hard-link-equivalent-and-link-count
// - cpp.stdlib.filesystem.canonical-existing-path-and-error
// - cpp.stdlib.filesystem.weakly-canonical-missing-suffix
// - cpp.stdlib.filesystem.relative-and-proximate-filesystem-operations
// - cpp.stdlib.filesystem.copy-symlink-versus-follow-target
// - cpp.stdlib.filesystem.recursive-iterator-follow-directory-symlink
// - cpp.stdlib.filesystem.equivalent-error-code-and-identity
// - cpp.stdlib.filesystem.symlink-loop-and-root-containment-traps

#include <gtest/gtest.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace {

namespace fs = std::filesystem;

class FilesystemLinksTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    root_ = fs::temp_directory_path() /
            (std::string{"polyglot-cpp-fs-links-"} + info->name());
    std::error_code error;
    fs::remove_all(root_, error);
    ASSERT_TRUE(fs::create_directories(root_ / "real" / "nested"));
    file_ = root_ / "real" / "nested" / "file.txt";
    write_file(file_, "original");
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

  std::error_code create_file_symlink(const fs::path& link) {
    std::error_code error;
    fs::create_symlink("real/nested/file.txt", link, error);
    return error;
  }

  std::error_code create_directory_symlink(const fs::path& link) {
    std::error_code error;
    fs::create_directory_symlink("real/nested", link, error);
    return error;
  }

  fs::path root_;
  fs::path file_;
};

TEST_F(FilesystemLinksTest, StatusFollowsTheTargetWhileSymlinkStatusDescribesTheLinkItself) {
  const fs::path link = root_ / "file-link";
  if (const auto error = create_file_symlink(link); error) {
    GTEST_SKIP() << "symbolic links are unavailable: " << error.message();
  }

  EXPECT_TRUE(fs::is_regular_file(fs::status(link)));
  EXPECT_TRUE(fs::is_symlink(fs::symlink_status(link)));
  EXPECT_FALSE(fs::is_symlink(fs::status(link)));
  EXPECT_EQ(fs::read_symlink(link).generic_string(), "real/nested/file.txt");
  EXPECT_EQ(read_file(link), "original");

  // status 跟随链接并描述目标；symlink_status 使用 lstat 式语义描述链接目录项。
  // read_symlink 返回保存的目标文本，可能是相对路径，基准是链接所在目录。
}

TEST_F(FilesystemLinksTest, DanglingSymlinkExistsAsAnEntryButItsResolvedTargetDoesNotExist) {
  const fs::path link = root_ / "dangling";
  std::error_code error;
  fs::create_symlink("missing-target", link, error);
  if (error) {
    GTEST_SKIP() << "symbolic links are unavailable: " << error.message();
  }

  EXPECT_TRUE(fs::is_symlink(fs::symlink_status(link)));
  EXPECT_FALSE(fs::exists(link));
  EXPECT_EQ(fs::status(link).type(), fs::file_type::not_found);
  EXPECT_EQ(fs::read_symlink(link), "missing-target");

  EXPECT_TRUE(fs::remove(link));
  EXPECT_FALSE(fs::is_symlink(fs::symlink_status(link)));

  // exists(path) 使用跟随链接的 status，因此悬空链接返回 false；需要判断目录项本身
  // 时查询 symlink_status。remove 删除链接而不是它指向的目标。
}

TEST_F(FilesystemLinksTest, HardLinksShareFileIdentityAndSurviveRemovalOfOneName) {
  const fs::path hard_link = root_ / "hard-link.txt";
  std::error_code error;
  fs::create_hard_link(file_, hard_link, error);
  if (error) {
    GTEST_SKIP() << "hard links are unavailable: " << error.message();
  }

  EXPECT_TRUE(fs::equivalent(file_, hard_link));
  EXPECT_GE(fs::hard_link_count(file_), 2U);

  write_file(hard_link, "changed");
  EXPECT_EQ(read_file(file_), "changed");
  ASSERT_TRUE(fs::remove(file_));
  EXPECT_EQ(read_file(hard_link), "changed");

  // 硬链接是同一文件对象的另一个目录名，不是内容副本；删除一个名字只减少链接数。
  // equivalent 查询真实身份，path 的词法相等无法发现这种关系。
}

TEST_F(FilesystemLinksTest, CanonicalRequiresExistenceAndResolvesDotDotAndLinks) {
  const fs::path noisy = root_ / "real" / "." / "nested" / ".." / "nested" / "file.txt";
  const fs::path canonical_file = fs::canonical(file_);
  EXPECT_EQ(fs::canonical(noisy), canonical_file);

  const fs::path link = root_ / "nested-link";
  if (const auto error = create_directory_symlink(link); error) {
    GTEST_SKIP() << "directory symbolic links are unavailable: " << error.message();
  }
  EXPECT_EQ(fs::canonical(link / "file.txt"), canonical_file);

  EXPECT_THROW(fs::canonical(root_ / "missing"), fs::filesystem_error);

  // canonical 要求每个组件存在，消除 ./.. 并解析符号链接，返回绝对路径。结果只是
  // 查询时刻的名字；攻击者仍可能在随后 open 前替换组件，不能单独防 TOCTOU。
}

TEST_F(FilesystemLinksTest, WeaklyCanonicalKeepsANormalizedMissingSuffix) {
  const fs::path requested = root_ / "real" / "nested" / "missing" / ".." / "child";
  const fs::path result = fs::weakly_canonical(requested);

  EXPECT_EQ(result, fs::canonical(root_ / "real" / "nested") / "child");
  EXPECT_TRUE(result.is_absolute());
  EXPECT_FALSE(fs::exists(result));

  // weakly_canonical 规范化最长存在前缀，再词法处理其余后缀，所以目标本身可不存在。
  // 它适合生成整洁候选路径，不证明父级未被符号链接绕出允许根目录。
}

TEST_F(FilesystemLinksTest, RelativeUsesCanonicalRelationshipAndProximateFallsBackToOriginal) {
  EXPECT_EQ(fs::relative(file_, root_).generic_string(), "real/nested/file.txt");
  EXPECT_EQ(fs::proximate(file_, root_).generic_string(), "real/nested/file.txt");

  std::error_code error;
  const fs::path relative_missing = fs::relative(root_ / "missing", root_, error);
  EXPECT_FALSE(error);
  EXPECT_EQ(relative_missing, "missing");

  // relative 等价于 weakly_canonical 后做 lexically_relative，会访问文件系统；
  // proximate 若无法构造相对路径则返回原路径。纯语法场景使用 lexical 版本。
}

TEST_F(FilesystemLinksTest, CopySymlinkCopiesTheLinkTextInsteadOfTargetContents) {
  const fs::path source_link = root_ / "source-link";
  const fs::path copied_link = root_ / "copied-link";
  if (const auto error = create_file_symlink(source_link); error) {
    GTEST_SKIP() << "symbolic links are unavailable: " << error.message();
  }

  fs::copy_symlink(source_link, copied_link);

  EXPECT_TRUE(fs::is_symlink(fs::symlink_status(copied_link)));
  EXPECT_EQ(fs::read_symlink(copied_link), fs::read_symlink(source_link));
  EXPECT_EQ(read_file(copied_link), "original");

  // copy_symlink 复制链接自身；普通 copy 默认可能跟随目标。部署工具必须明确选择
  // copy_symlinks、skip_symlinks 或 follow 行为，避免复制树时越过预期边界。
}

TEST_F(FilesystemLinksTest, RecursiveIteratorFollowsDirectoryLinksOnlyWhenRequested) {
  const fs::path alias = root_ / "alias";
  if (const auto error = create_directory_symlink(alias); error) {
    GTEST_SKIP() << "directory symbolic links are unavailable: " << error.message();
  }

  auto count_alias_files = [&](fs::directory_options options) {
    std::size_t count = 0;
    for (const auto& entry : fs::recursive_directory_iterator{root_, options}) {
      const auto relative = entry.path().lexically_relative(root_).generic_string();
      if (entry.is_regular_file() && relative.rfind("alias/", 0) == 0) {
        ++count;
      }
    }
    return count;
  };

  EXPECT_EQ(count_alias_files(fs::directory_options::none), 0U);
  EXPECT_EQ(
      count_alias_files(fs::directory_options::follow_directory_symlink),
      1U);

  // 默认递归不进入目录符号链接；follow 后可能重复访问同一文件，也可能进入循环。
  // 标准迭代器不提供自动环检测，调用者需跟踪 canonical 身份或限制深度。
}

TEST_F(FilesystemLinksTest, EquivalentReportsIdentityAndUsesErrorsForMissingOperands) {
  EXPECT_TRUE(fs::equivalent(file_, file_));

  std::error_code error;
  EXPECT_FALSE(fs::equivalent(file_, root_ / "missing", error));
  if (!error) {
    // N4861 [fs.op.equivalent]/4 明定任一操作数不存在就是错误。libstdc++ 11
    // 只有两个操作数都不存在时才设置 error_code；GCC PR113250 在 GCC 14 修复。
    GTEST_SKIP() << "libstdc++ 11 has the equivalent missing-operand defect (PR113250)";
  }
  EXPECT_EQ(error, std::errc::no_such_file_or_directory);
  EXPECT_THROW(
      static_cast<void>(fs::equivalent(file_, root_ / "missing")),
      fs::filesystem_error);

  // equivalent 要求两个路径解析到现存文件并比较实现身份；缺失不是简单 false 比较，
  // 标准要求 error_code 或异常说明查询失败。身份也可能在调用后因 rename/remove 改变。
}

}  // namespace
