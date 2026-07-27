// 接口行为和实现层次。
// 共同问题：版本、实现和运行平台如何分开描述；如何验证真正可用的接口；
// 为什么字符串版本比较不能替代结构化版本与行为检测。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/cpp/language/
// polyglot-related+: test_019_preprocessor_macros_feature_detection_and_translation.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <string>
#include <thread>
#include <version>

namespace {

template <typename Type>
concept ErasablePrefix = requires(Type value) {
  { value.starts_with("prefix-") } -> std::same_as<bool>;
  { value.erase(0, 7) } -> std::same_as<Type&>;
};

TEST(RuntimeLayerConcept, LanguageCompilerAndLibraryReportSeparateVersions) {
  EXPECT_GE(__cplusplus, 202002L);
#ifdef __GNUC__
  EXPECT_EQ(__GNUC__, 11);
#else
  FAIL() << "sources.lock 锁定 GCC 11.4";
#endif
#ifdef _GLIBCXX_RELEASE
  EXPECT_EQ(_GLIBCXX_RELEASE, 11);
#else
  FAIL() << "锁定的 libstdc++ 应声明 _GLIBCXX_RELEASE";
#endif
}

TEST(RuntimeLayerConcept, FeatureMacroAndUsableInterfaceAreBothVerified) {
#ifdef __cpp_lib_jthread
  static_assert(__cpp_lib_jthread >= 201911L);
  std::jthread worker{[] {}};
  EXPECT_TRUE(worker.joinable());
#else
  FAIL() << "锁定的 C++20 标准库应提供 jthread";
#endif
}

TEST(RuntimeLayerConcept, RequiresChecksTheExpressionContractActuallyNeeded) {
  constexpr bool string_supports_contract = ErasablePrefix<std::string>;
  constexpr bool integer_supports_contract = ErasablePrefix<int>;
  static_assert(string_supports_contract);
  static_assert(!integer_supports_contract);

  EXPECT_TRUE(string_supports_contract);
  EXPECT_FALSE(integer_supports_contract);
}

}  // namespace
