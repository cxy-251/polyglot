// 文件、目录、元数据与链接。
// 共同问题：如何创建和读取文件；目录遍历返回什么；元数据描述链接还是目标；
// 硬链接与符号链接共享哪些身份。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: file_directory_metadata_and_links
// polyglot-related: languages/cpp/standard_library/15_filesystem/
// polyglot-related+: test_139_symlinks_hard_links_canonical_relative_and_equivalent_paths.cpp

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <set>
#include <string>

namespace {

namespace fs = std::filesystem;

class FilesConcept : public testing::Test {
 protected:
  void SetUp() override {
    root_ = fs::temp_directory_path() / "polyglot-concept-files";
    fs::remove_all(root_);
    fs::create_directories(root_);
  }

  void TearDown() override {
    fs::remove_all(root_);
  }

  fs::path root_;
};

TEST_F(FilesConcept, FileLifecycleAndMetadataAreSeparateOperations) {
  const fs::path file = root_ / "note.txt";
  std::ofstream{file} << "value";

  EXPECT_TRUE(fs::is_regular_file(file));
  EXPECT_EQ(fs::file_size(file), 5U);
  fs::rename(file, root_ / "renamed.txt");
  EXPECT_FALSE(fs::exists(file));
}

TEST_F(FilesConcept, DirectoryIteratorVisitsImmediateChildren) {
  fs::create_directory(root_ / "nested");
  std::ofstream{root_ / "note.txt"} << "value";
  std::set<std::string> names;

  for (const fs::directory_entry& entry : fs::directory_iterator{root_}) {
    names.insert(entry.path().filename().string());
  }

  EXPECT_EQ(names, (std::set<std::string>{"nested", "note.txt"}));
}

TEST_F(FilesConcept, HardLinksReferToEquivalentFilesystemObjects) {
  const fs::path original = root_ / "original.txt";
  const fs::path alias = root_ / "alias.txt";
  std::ofstream{original} << "value";
  fs::create_hard_link(original, alias);

  EXPECT_TRUE(fs::equivalent(original, alias));
  EXPECT_EQ(fs::hard_link_count(original), 2U);
}

TEST_F(FilesConcept, StatusFollowsSymlinkButSymlinkStatusDoesNot) {
  const fs::path target = root_ / "target.txt";
  const fs::path link = root_ / "link.txt";
  std::ofstream{target} << "value";
  fs::create_symlink(target, link);

  EXPECT_TRUE(fs::is_symlink(fs::symlink_status(link)));
  EXPECT_TRUE(fs::is_regular_file(fs::status(link)));
}

}  // namespace
