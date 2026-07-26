// polyglot-covers:
// - cpp.stdlib.filesystem.path-native-generic-and-preferred-format
// - cpp.stdlib.filesystem.path-append-versus-concatenate
// - cpp.stdlib.filesystem.path-decomposition-root-parent-filename-stem-extension
// - cpp.stdlib.filesystem.path-query-empty-and-has-components
// - cpp.stdlib.filesystem.path-modifiers-remove-replace-and-swap
// - cpp.stdlib.filesystem.path-component-iteration
// - cpp.stdlib.filesystem.path-lexically-normal-relative-and-proximate
// - cpp.stdlib.filesystem.path-comparison-order-and-hash
// - cpp.stdlib.filesystem.path-stream-quoted-round-trip
// - cpp.stdlib.filesystem.path-code-unit-and-encoding-boundaries

#include <gtest/gtest.h>

#include <algorithm>
#include <filesystem>
#include <functional>
#include <sstream>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

namespace fs = std::filesystem;

TEST(FilesystemPathFormats, GenericObserversUseSlashesWhileNativeStorageIsPlatformDefined) {
  const fs::path path{"alpha/beta/file.txt"};

  EXPECT_EQ(path.generic_string(), "alpha/beta/file.txt");
  EXPECT_FALSE(path.native().empty());
  EXPECT_FALSE(path.is_absolute());
  EXPECT_TRUE(path.is_relative());
  static_assert(std::is_same_v<fs::path::value_type, char> ||
                std::is_same_v<fs::path::value_type, wchar_t>);

  fs::path preferred{"alpha/beta"};
  preferred.make_preferred();
  EXPECT_EQ(preferred.generic_string(), "alpha/beta");

  // native() 的字符类型与分隔符由平台决定；generic_* 始终用 '/'，适合展示和
  // 可移植比较组件。path 只管理路径语法，不保证字符编码能在另一平台往返。
}

TEST(FilesystemPathComposition, SlashAppendsAComponentWhilePlusConcatenatesRawPathText) {
  fs::path hierarchical{"root"};
  hierarchical /= "child";
  hierarchical /= "file";

  fs::path extension{"archive"};
  extension += ".tar";
  extension.concat(".gz");

  EXPECT_EQ(hierarchical.generic_string(), "root/child/file");
  EXPECT_EQ(extension.generic_string(), "archive.tar.gz");
  EXPECT_EQ((fs::path{"root"} / "child").generic_string(), "root/child");

  // /= 与 operator/ 按路径组件加入分隔符，并处理右侧 root-name/root-directory；
  // +=/concat 只是拼接代码单元，适合扩展名片段，不能代替目录连接。
}

TEST(FilesystemPathDecomposition, FilenameStemAndExtensionOperateOnTheLastComponent) {
  const fs::path archive{"usr/local/archive.tar.gz"};

  EXPECT_EQ(archive.root_path(), fs::path{});
  EXPECT_EQ(archive.parent_path().generic_string(), "usr/local");
  EXPECT_EQ(archive.filename(), "archive.tar.gz");
  EXPECT_EQ(archive.stem(), "archive.tar");
  EXPECT_EQ(archive.extension(), ".gz");
  EXPECT_EQ(archive.relative_path(), archive);

  const fs::path dotfile{".profile"};
  EXPECT_EQ(dotfile.stem(), ".profile");
  EXPECT_TRUE(dotfile.extension().empty());

  const fs::path trailing{"dir/"};
  EXPECT_TRUE(trailing.filename().empty());
  EXPECT_EQ(trailing.parent_path(), "dir");

  // extension 包含前导点；以单个点开头的普通 dotfile 不被拆成空 stem+扩展名。
  // 末尾分隔符代表空 filename 组件，不能与路径 "dir" 完全等同看待。
}

TEST(FilesystemPathQueries, EmptyAndComponentPresenceArePurelySyntactic) {
  const fs::path empty;
  const fs::path relative{"dir/file.txt"};

  EXPECT_TRUE(empty.empty());
  EXPECT_FALSE(empty.has_filename());
  EXPECT_TRUE(relative.has_relative_path());
  EXPECT_TRUE(relative.has_parent_path());
  EXPECT_TRUE(relative.has_filename());
  EXPECT_TRUE(relative.has_stem());
  EXPECT_TRUE(relative.has_extension());
  EXPECT_FALSE(relative.has_root_name());
  EXPECT_FALSE(relative.has_root_directory());

  // has_* 只查看解析出的路径组件，不访问文件系统；有 filename 不代表文件存在，
  // 有 extension 也不代表操作系统把它当某种文件类型。
}

TEST(FilesystemPathModifiers, RemoveAndReplaceOperateOnSyntacticComponents) {
  fs::path path{"dir/report.txt"};
  path.replace_extension("md");
  EXPECT_EQ(path.generic_string(), "dir/report.md");

  path.replace_filename("summary.csv");
  EXPECT_EQ(path.generic_string(), "dir/summary.csv");

  path.remove_filename();
  EXPECT_EQ(path.generic_string(), "dir/");
  EXPECT_TRUE(path.filename().empty());

  fs::path other{"other"};
  path.swap(other);
  EXPECT_EQ(path, "other");
  EXPECT_EQ(other.generic_string(), "dir/");

  path.clear();
  EXPECT_TRUE(path.empty());

  // replace_extension 会按路径规则补点；remove_filename 保留父目录的尾分隔语义。
  // 这些操作不重命名磁盘对象，只修改 path 值。
}

TEST(FilesystemPathIteration, IteratorYieldsParsedComponentsNotIndividualCharacters) {
  const fs::path path{"alpha/beta/../gamma.txt"};
  std::vector<std::string> components;

  std::transform(
      path.begin(),
      path.end(),
      std::back_inserter(components),
      [](const fs::path& component) { return component.generic_string(); });

  EXPECT_EQ(components, (std::vector<std::string>{"alpha", "beta", "..", "gamma.txt"}));

  // 迭代器暴露 root-name、root-directory、文件名等路径组件；它不会自动消除 '.'
  // 或 '..'。修改 path 会使其迭代器失效。
}

TEST(FilesystemPathLexicalAlgorithms, NormalizationAndRelativizationDoNotTouchTheFilesystem) {
  const fs::path noisy{"alpha/./beta/../gamma"};
  EXPECT_EQ(noisy.lexically_normal().generic_string(), "alpha/gamma");

  const fs::path target{"alpha/beta/file.txt"};
  const fs::path base{"alpha/docs"};
  EXPECT_EQ(target.lexically_relative(base).generic_string(), "../beta/file.txt");
  EXPECT_EQ(target.lexically_proximate(base).generic_string(), "../beta/file.txt");

  EXPECT_EQ(fs::path{"a/../../b"}.lexically_normal().generic_string(), "../b");

  // lexical 算法只按组件计算，不解析符号链接，也不要求路径存在。relative/canonical
  // 等文件系统操作会考虑真实目录关系，安全敏感路径不能只做词法规范化。
}

TEST(FilesystemPathComparison, EqualityIsLexicalAndEqualValuesHaveEqualHashes) {
  const fs::path first{"alpha/beta"};
  const fs::path same{"alpha/beta"};
  const fs::path noisy{"alpha/./beta"};

  EXPECT_EQ(first, same);
  EXPECT_EQ(std::hash<fs::path>{}(first), std::hash<fs::path>{}(same));
  EXPECT_NE(first, noisy);
  EXPECT_EQ(first, noisy.lexically_normal());
  EXPECT_LT(fs::path{"alpha/a"}.compare(fs::path{"alpha/b"}), 0);

  // path 相等比较路径表示的组件，不查询两个名字是否指向同一文件；硬链接/符号链接
  // 身份要用 equivalent。hash 只保证相等 path 同值，具体数值不可持久化。
}

TEST(FilesystemPathStreams, InserterQuotesWhitespaceAndExtractorReadsTheSameRepresentation) {
  const fs::path original{"folder/a b.txt"};
  std::ostringstream output;
  output << original;
  EXPECT_EQ(output.str(), R"("folder/a b.txt")");

  std::istringstream input{output.str()};
  fs::path restored;
  input >> restored;
  EXPECT_EQ(restored, original);

  // path 流操作按 std::quoted 规则保护空格与转义字符，因此不是简单输出 string()。
  // 该表示适合同一 locale/平台的流往返，不是跨系统路径交换格式。
}

TEST(FilesystemPathEncoding, DifferentCodeUnitFactoriesDoNotPromiseUnicodeNormalization) {
  const fs::path ascii_from_narrow{"folder/file"};
  const fs::path ascii_from_utf8 = fs::u8path(u8"folder/file");

  EXPECT_EQ(ascii_from_narrow, ascii_from_utf8);
  EXPECT_EQ(ascii_from_utf8.u8string(), u8"folder/file");

  // u8path 按 UTF-8 构造平台路径，但 C++20 已让 path 直接支持 char8_t 来源；接口
  // 不执行 Unicode NFC/NFD 规范化，也不能保证任意字节文件名能转成所有字符串类型。
}

}  // namespace
