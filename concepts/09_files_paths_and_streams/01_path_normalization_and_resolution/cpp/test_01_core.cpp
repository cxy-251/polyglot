// 路径规范化与解析。
// 共同问题：路径操作是纯词法计算还是访问文件系统；相对路径以什么为基准；
// 规范化、绝对化与解析符号链接是否等价。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: path_normalization_and_resolution
// polyglot-related: languages/cpp/standard_library/15_filesystem/
// polyglot-related+: test_135_path_construction_decomposition_modifiers_and_lexical_algorithms.cpp

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>

namespace {

namespace fs = std::filesystem;

class PathConcept : public testing::Test {
 protected:
  void SetUp() override {
    root_ = fs::temp_directory_path() / "polyglot-concept-paths";
    fs::remove_all(root_);
    fs::create_directories(root_ / "target");
  }

  void TearDown() override {
    fs::remove_all(root_);
  }

  fs::path root_;
};

TEST_F(PathConcept, LexicallyNormalDoesNotRequirePathToExist) {
  const fs::path input = "workspace/../result.txt";

  EXPECT_EQ(input.lexically_normal(), fs::path{"result.txt"});
  EXPECT_TRUE(input.is_relative());
}

TEST_F(PathConcept, AbsoluteUsesCurrentDirectoryButNeedNotCanonicalize) {
  const fs::path relative = "missing/../result.txt";
  const fs::path absolute = fs::absolute(relative);

  EXPECT_TRUE(absolute.is_absolute());
  EXPECT_EQ(absolute.filename(), "result.txt");
}

TEST_F(PathConcept, CanonicalConsultsFilesystemAndFollowsSymlink) {
  const fs::path link = root_ / "alias";
  fs::create_directory_symlink(root_ / "target", link);

  EXPECT_EQ(fs::canonical(link), fs::canonical(root_ / "target"));
}

TEST_F(PathConcept, WeaklyCanonicalAllowsMissingTail) {
  const fs::path result = fs::weakly_canonical(root_ / "target/../missing/file.txt");

  EXPECT_EQ(result, root_ / "missing/file.txt");

  // path 的 preferred_separator 和根名称由平台决定，不应硬编码成所有系统都使用斜杠。
}

}  // namespace
