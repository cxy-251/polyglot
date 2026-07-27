// 包解析、导出与可见性。
// 共同问题：包名如何解析到文件；包入口如何组织公共 API；私有名称是否强制隐藏；
// 相对导入以什么为基准。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/cpp/language/test_015_namespaces_using_lookup_and_adl.cpp
// polyglot-related: languages/cpp/language/test_020_translation_units_odr_inline_and_modules.cpp

#include <gtest/gtest.h>

#include <concepts>

namespace {

#if __has_include(<concepts>)
constexpr bool kConceptsHeaderIsResolvable = true;
#else
constexpr bool kConceptsHeaderIsResolvable = false;
#endif

namespace library {

class Service {
 public:
  int run() const { return state_; }

 private:
  int state_ = 1;
};

namespace detail {

int helper() {
  return 2;
}

}  // namespace detail
}  // namespace library

template <typename T>
concept ExposesState = requires(T value) {
  value.state_;
};

TEST(PackageVisibilityConcept, NamespaceGroupsNamesButDoesNotHideDetailNamespace) {
  library::Service service;

  EXPECT_EQ(service.run(), 1);
  EXPECT_EQ(library::detail::helper(), 2);
}

TEST(PackageVisibilityConcept, ClassAccessControlEnforcesPrivateState) {
  static_assert(!ExposesState<library::Service>);
}

TEST(PackageVisibilityConcept, HeaderSearchAndLibraryResolutionAreBuildConcerns) {
  EXPECT_TRUE(kConceptsHeaderIsResolvable);

  // C++20 标准定义 translation unit、linkage 和 modules，不定义 Python/npm 式包仓库解析。
}

TEST(PackageVisibilityConcept, IncludePathDoesNotCreateARuntimePackageObject) {
  static_assert(std::same_as<decltype(library::detail::helper()), int>);
}

}  // namespace
