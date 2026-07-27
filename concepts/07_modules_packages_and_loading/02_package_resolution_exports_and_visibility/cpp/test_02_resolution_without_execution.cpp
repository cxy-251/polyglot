// 解析、执行与相对基准。
// 共同问题：定位模块是否等于执行模块；相对说明符由什么上下文解释；
// 导出列表或命名约定是否构成真正访问控制。
//
// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/cpp/language/test_015_namespaces_using_lookup_and_adl.cpp
// polyglot-related: languages/cpp/language/test_020_translation_units_odr_inline_and_modules.cpp

#include <gtest/gtest.h>

#include <concepts>

#include "support/package_api.hpp"

namespace {

#if __has_include("support/package_api.hpp")
constexpr bool kPackageHeaderIsResolvable = true;
#else
constexpr bool kPackageHeaderIsResolvable = false;
#endif

template <typename T>
concept ExposesState = requires(T value) {
  value.state_;
};

TEST(PackageResolutionConcept, IncludeResolutionMakesDeclarationsAvailableAtCompileTime) {
  static_assert(kPackageHeaderIsResolvable);
  static_assert(!ExposesState<package_api::Service>);

  EXPECT_EQ(package_api::public_value(), 1);
  EXPECT_EQ(package_api::Service{}.read(), 3);
}

TEST(PackageResolutionConcept, DetailNamespaceIsConventionRatherThanAccessControl) {
  EXPECT_EQ(package_api::detail::helper(), 2);

  // header 名称按源文件位置与编译器 include path 解析；链接器再解析外部定义。C++20
  // 标准没有从 cwd 运行期查找包的规则，namespace detail 也不隐藏名字。
}

}  // namespace
