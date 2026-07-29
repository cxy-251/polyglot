// 运行时能力、版本与特性检测。
// 共同问题：代码如何识别当前实现和版本；如何检测某项能力是否真正存在；
// 何时应检测行为或接口而不是脆弱地比较版本字符串。
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
concept HasSize = requires(const Type& value) {
  { value.size() } -> std::convertible_to<std::size_t>;
};

TEST(RuntimeCapabilityConcept, LanguageVersionUsesStructuredMacroValue) {
  static_assert(__cplusplus >= 202002L);

  EXPECT_GE(__cplusplus, 202002L);
}

TEST(RuntimeCapabilityConcept, FeatureTestMacrosDescribeLibraryFacilities) {
#ifdef __cpp_lib_concepts
  EXPECT_GE(__cpp_lib_concepts, 202002L);
#else
  FAIL() << "锁定的 C++20 标准库应声明 concepts 支持";
#endif
}

TEST(RuntimeCapabilityConcept, RequiresExpressionChecksUsableInterface) {
  constexpr bool string_has_size = HasSize<std::string>;
  constexpr bool int_has_size = HasSize<int>;
  static_assert(string_has_size);
  static_assert(!int_has_size);

  EXPECT_TRUE(string_has_size);
  EXPECT_FALSE(int_has_size);
}

TEST(RuntimeCapabilityConcept, FeatureMacroAndUsableInterfaceAreBothChecked) {
#ifdef __cpp_lib_jthread
  static_assert(__cpp_lib_jthread >= 201911L);
  std::jthread worker{[] {}};
  EXPECT_TRUE(worker.joinable());
#else
  GTEST_SKIP() << "当前标准库未提供 jthread";
#endif

  // 编译器、语言模式和标准库版本是三个维度；优先使用特性宏或 requires 检测具体接口。
}

}  // namespace
