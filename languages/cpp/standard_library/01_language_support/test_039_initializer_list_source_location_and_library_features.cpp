// polyglot-covers:
// - cpp.stdlib.language-support.initializer-list-view
// - cpp.stdlib.language-support.initializer-list-const-elements
// - cpp.stdlib.language-support.initializer-list-backing-array-lifetime
// - cpp.stdlib.language-support.source-location
// - cpp.stdlib.language-support.source-location-default-argument-call-site
// - cpp.stdlib.language-support.version-header
// - cpp.stdlib.language-support.library-feature-test-macros

#include <gtest/gtest.h>

#include <cstdint>
#include <initializer_list>
#include <source_location>
#include <string>
#include <type_traits>
#include <version>

namespace {

int sum(std::initializer_list<int> values) {
  int result = 0;
  for (int value : values) {
    result += value;
  }
  return result;
}

struct CallSite {
  std::string file;
  std::string function;
  std::uint_least32_t line;
  std::uint_least32_t column;
};

CallSite capture_call_site(
    const std::source_location location = std::source_location::current()) {
  return {
      location.file_name(),
      location.function_name(),
      location.line(),
      location.column(),
  };
}

TEST(InitializerList, LightweightViewExposesOnlyConstElements) {
  const std::initializer_list<int> values{2, 3, 5};

  EXPECT_EQ(values.size(), 3U);
  EXPECT_EQ(sum(values), 10);
  static_assert(std::is_same_v<decltype(*values.begin()), const int&>);

  // initializer_list 通常只保存 backing array 的首地址与长度；复制 list 不复制元素。
  // 元素始终是 const，因此不能把 initializer_list 当作可变容器或移动元素的来源。
}

TEST(InitializerList, BracedListCanSelectAListTakingOverload) {
  EXPECT_EQ(sum({1, 4, 9}), 14);
  EXPECT_EQ(sum({}), 0);

  // braced-init-list 本身没有普通表达式类型，但可初始化 initializer_list 参数。若重载集
  // 同时有 initializer_list 和其他构造形式，列表候选通常优先，可能改变重载选择。
}

TEST(InitializerList, BackingArrayLifetimeFollowsTheOwningListObject) {
  std::initializer_list<std::string> words{"poly", "glot"};
  const std::string* first = words.begin();
  auto copied_view = words;

  EXPECT_EQ(first, copied_view.begin());
  EXPECT_EQ(copied_view.begin()[0] + copied_view.begin()[1], "polyglot");

  // 用 initializer_list 对象初始化时，backing array 的寿命延长到该对象寿命结束；复制
  // 只共享同一数组。函数若保存参数的 begin() 到调用表达式之后，通常会留下悬空指针。
}

TEST(SourceLocation, DefaultArgumentCapturesTheCallSiteNotTheHelperDefinition) {
  const auto expected_line = static_cast<std::uint_least32_t>(__LINE__ + 1);
  const CallSite site = capture_call_site();

  EXPECT_EQ(site.line, expected_line);
  EXPECT_NE(site.file.find("test_039_initializer_list_source_location"), std::string::npos);
  EXPECT_FALSE(site.function.empty());

  // source_location::current() 放在默认实参中时，在调用点求值，适合日志 API 自动携带
  // 文件、行和函数。具体 file/function 字符串格式与 column 精度属于实现定义。
}

TEST(SourceLocation, ExplicitLocationCanBeForwardedWithoutLosingTheOrigin) {
  const auto origin = std::source_location::current();
  const CallSite forwarded = capture_call_site(origin);

  EXPECT_EQ(forwarded.line, origin.line());
  EXPECT_EQ(forwarded.file, origin.file_name());

  // 包装层若不显式转发 location，而是在内部再次调用 current()，日志会记录包装函数而非
  // 业务调用点。把 source_location 作为末尾默认参数可同时保留易用性与原始位置。
}

TEST(FeatureTestMacros, VersionHeaderCentralizesLibraryCapabilityDetection) {
#ifdef __cpp_lib_source_location
  static_assert(__cpp_lib_source_location >= 201907L);
#else
  FAIL() << "C++20 baseline must expose std::source_location";
#endif

#ifdef __cpp_lib_three_way_comparison
  static_assert(__cpp_lib_three_way_comparison >= 201907L);
#else
  FAIL() << "C++20 baseline must expose comparison support";
#endif

  // <version> 集中公开 __cpp_lib_* 宏，适合在不包含具体功能头文件前做条件编译。版本宏
  // 比只检查 __cplusplus 更精确：语言模式开启不代表某个标准库实现已经完成全部组件。
}

}  // namespace
