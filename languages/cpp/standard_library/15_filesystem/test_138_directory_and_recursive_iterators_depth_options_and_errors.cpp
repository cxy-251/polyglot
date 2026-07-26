// polyglot-covers:
// - cpp.stdlib.filesystem.directory-iterator-immediate-entries-and-unspecified-order
// - cpp.stdlib.filesystem.directory-iterator-input-range-and-end-sentinel
// - cpp.stdlib.filesystem.directory-entry-observers-during-iteration
// - cpp.stdlib.filesystem.recursive-directory-iterator-depth
// - cpp.stdlib.filesystem.recursion-pending-and-disable-recursion-pending
// - cpp.stdlib.filesystem.recursive-directory-iterator-pop
// - cpp.stdlib.filesystem.iterator-error-code-construction-and-increment
// - cpp.stdlib.filesystem.directory-options-bitmask
// - cpp.stdlib.filesystem.iterating-while-mutating-unspecified-trap

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <system_error>
#include <vector>

namespace {

namespace fs = std::filesystem;

class FilesystemIteratorTest : public ::testing::Test {
 protected:
  void SetUp() override {
    const auto* info = ::testing::UnitTest::GetInstance()->current_test_info();
    root_ = fs::temp_directory_path() /
            (std::string{"polyglot-cpp-fs-iter-"} + info->name());
    std::error_code error;
    fs::remove_all(root_, error);
    ASSERT_TRUE(fs::create_directories(root_ / "a" / "deep"));
    ASSERT_TRUE(fs::create_directories(root_ / "b"));
    ASSERT_TRUE(fs::create_directories(root_ / "empty"));
    write(root_ / "root.txt");
    write(root_ / "a" / "one.txt");
    write(root_ / "a" / "deep" / "two.txt");
    write(root_ / "b" / "three.txt");
  }

  void TearDown() override {
    std::error_code error;
    fs::remove_all(root_, error);
  }

  static void write(const fs::path& path) {
    std::ofstream output{path};
    ASSERT_TRUE(output.is_open());
    output << path.filename().string();
  }

  fs::path root_;
};

TEST_F(FilesystemIteratorTest, DirectoryIteratorVisitsOnlyImmediateEntriesInUnspecifiedOrder) {
  std::vector<std::string> names;
  for (const fs::directory_entry& entry : fs::directory_iterator{root_}) {
    names.push_back(entry.path().filename().string());
  }
  std::sort(names.begin(), names.end());

  EXPECT_EQ(names, (std::vector<std::string>{"a", "b", "empty", "root.txt"}));

  // directory_iterator 不递归，且遍历顺序未指定；测试先收集再排序。遍历开始后
  // 增删目录项是否能被观察也未指定，不应边迭代边依赖实时快照语义。
}

TEST(DirectoryIteratorConcepts, ItIsASinglePassInputIteratorWithADefaultEndValue) {
  static_assert(std::input_iterator<fs::directory_iterator>);
  static_assert(!std::forward_iterator<fs::directory_iterator>);
  static_assert(std::same_as<fs::directory_iterator::value_type, fs::directory_entry>);

  const fs::directory_iterator end;
  EXPECT_EQ(end, fs::directory_iterator{});

  // 迭代器副本共享单趟遍历状态，不能像 forward iterator 那样保存副本后独立重走。
  // 默认构造值充当 end；解引用或递增 end 都违反前置条件。
}

TEST_F(FilesystemIteratorTest, DirectoryEntriesExposePathTypeAndSizeWithoutOpeningFiles) {
  std::size_t regular_files = 0;
  std::size_t directories = 0;
  for (const auto& entry : fs::directory_iterator{root_}) {
    if (entry.is_regular_file()) {
      ++regular_files;
      EXPECT_GT(entry.file_size(), 0U);
    } else if (entry.is_directory()) {
      ++directories;
    }
  }

  EXPECT_EQ(regular_files, 1U);
  EXPECT_EQ(directories, 3U);

  // directory_entry 的类型/大小观察可能使用枚举时缓存的信息，也可能再次查询；
  // 它不是打开的文件句柄，检查后到实际使用之间仍存在 TOCTOU 竞态。
}

TEST_F(FilesystemIteratorTest, RecursiveIteratorFindsNestedFilesAndReportsTheirDepth) {
  std::vector<std::string> files;
  std::vector<int> depths;

  for (fs::recursive_directory_iterator current{root_}, end; current != end; ++current) {
    if (current->is_regular_file()) {
      files.push_back(fs::relative(current->path(), root_).generic_string());
      depths.push_back(current.depth());
    }
  }
  std::sort(files.begin(), files.end());

  EXPECT_EQ(
      files,
      (std::vector<std::string>{
          "a/deep/two.txt", "a/one.txt", "b/three.txt", "root.txt"}));
  EXPECT_NE(std::find(depths.begin(), depths.end(), 2), depths.end());
  EXPECT_NE(std::find(depths.begin(), depths.end(), 0), depths.end());

  // depth=0 是构造时目录的直接子项；进入一层目录后加一。顺序仍未指定，且目录项
  // 本身也会被访问，只是本例筛选普通文件。
}

TEST_F(FilesystemIteratorTest, DisableRecursionPendingSkipsOnlyTheCurrentDirectorySubtree) {
  std::vector<std::string> files;
  fs::recursive_directory_iterator current{root_};
  const fs::recursive_directory_iterator end;

  for (; current != end; ++current) {
    if (current->is_directory() && current->path().filename() == "a") {
      EXPECT_TRUE(current.recursion_pending());
      current.disable_recursion_pending();
      EXPECT_FALSE(current.recursion_pending());
    }
    if (current->is_regular_file()) {
      files.push_back(fs::relative(current->path(), root_).generic_string());
    }
  }
  std::sort(files.begin(), files.end());

  EXPECT_EQ(files, (std::vector<std::string>{"b/three.txt", "root.txt"}));

  // disable_recursion_pending 只影响下一次对当前目录的递增，不永久关闭其他目录递归。
}

TEST_F(FilesystemIteratorTest, PopReturnsToTheParentTraversalAndCanReachEnd) {
  const fs::path chain = root_ / "chain";
  ASSERT_TRUE(fs::create_directories(chain / "inner"));
  write(chain / "inner" / "leaf.txt");

  fs::recursive_directory_iterator current{chain};
  ASSERT_NE(current, fs::recursive_directory_iterator{});
  EXPECT_EQ(current->path().filename(), "inner");
  EXPECT_EQ(current.depth(), 0);

  ++current;
  ASSERT_NE(current, fs::recursive_directory_iterator{});
  EXPECT_EQ(current->path().filename(), "leaf.txt");
  EXPECT_EQ(current.depth(), 1);

  current.pop();
  EXPECT_EQ(current, fs::recursive_directory_iterator{});

  // pop 停止当前目录层并恢复父层的下一个条目；若父层也已结束，就成为 end。
  // 在 depth()==0 时调用 pop 直接结束整个遍历。
}

TEST_F(FilesystemIteratorTest, ErrorCodeConstructionAndIncrementAvoidThrowing) {
  const fs::path missing = root_ / "missing";
  std::error_code error;
  fs::directory_iterator missing_iterator{missing, error};

  EXPECT_TRUE(error);
  EXPECT_EQ(missing_iterator, fs::directory_iterator{});

  error.clear();
  fs::directory_iterator current{root_, error};
  ASSERT_FALSE(error);
  ASSERT_NE(current, fs::directory_iterator{});
  current.increment(error);
  EXPECT_FALSE(error);

  // error_code 构造失败得到 end；increment(ec) 成功时清 ec。遍历中目录被删除或
  // 权限改变仍可能在后续 increment 失败，因此错误处理不能只放在构造处。
}

TEST(DirectoryOptions, FlagsComposeButMutuallyDifferentPoliciesNeedIntentionalUse) {
  constexpr auto options =
      fs::directory_options::follow_directory_symlink |
      fs::directory_options::skip_permission_denied;

  static_assert(
      (options & fs::directory_options::follow_directory_symlink) !=
      fs::directory_options::none);
  EXPECT_NE(options, fs::directory_options::none);

  // follow_directory_symlink 可能引入循环，skip_permission_denied 会静默跳过子树。
  // 两者都是策略而非“更稳妥默认值”；需要完整性审计时跳过权限错误尤其危险。
}

}  // namespace
