// 区域可用性和状态边界。
// 共同问题：区域数据缺失时如何失败；排序是否等于代码点顺序；
// 区域配置属于显式对象还是可泄漏到其他代码的进程状态。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/cpp/standard_library/16_localization/
// polyglot-related+: test_141_locale_objects_categories_facets_and_global_state.cpp

#include <gtest/gtest.h>

#include <iomanip>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

class CommaPunctuation final : public std::numpunct<char> {
 protected:
  char do_decimal_point() const override { return ','; }
  char do_thousands_sep() const override { return '.'; }
  std::string do_grouping() const override { return "\3"; }
};

std::string formatNumber(const std::locale& locale) {
  std::ostringstream output;
  output.imbue(locale);
  output << std::fixed << std::setprecision(1) << 1234.5;
  return output.str();
}

TEST(LocaleBoundaryConcept, ExplicitLocaleObjectsKeepIndependentFormattingRules) {
  const std::locale classic = std::locale::classic();
  const std::locale comma{classic, new CommaPunctuation};

  EXPECT_EQ(formatNumber(classic), "1234.5");
  EXPECT_EQ(formatNumber(comma), "1.234,5");
  EXPECT_EQ(formatNumber(classic), "1234.5");
}

TEST(LocaleBoundaryConcept, MissingNamedLocaleFailsAtConstruction) {
  EXPECT_THROW(
      static_cast<void>(std::locale{"polyglot_LOCALE_that_does_not_exist"}),
      std::runtime_error);

  // classic locale 总是可用；其他名称由实现和宿主安装决定，先构造再处理失败。
}

TEST(LocaleBoundaryConcept, ClassicCollationIsNotANaturalLanguageGuarantee) {
  const auto& facet = std::use_facet<std::collate<char>>(std::locale::classic());
  const std::string left = "z";
  const std::string right = "\xC3\xA4";
  const int collated = facet.compare(
      left.data(), left.data() + left.size(), right.data(), right.data() + right.size());

  EXPECT_EQ(collated < 0, left.compare(right) < 0);

  // compare 只保证结果的符号，不保证返回值等于 basic_string::compare 的距离。
}

}  // namespace
