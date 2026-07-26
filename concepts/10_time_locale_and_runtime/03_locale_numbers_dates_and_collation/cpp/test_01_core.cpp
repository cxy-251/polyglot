// 区域化数字、日期与排序。
// 共同问题：数字和日期如何按区域呈现；文本排序是否等于码点顺序；
// 区域设置是显式对象还是进程全局状态；缺少区域数据时如何处理。
//
// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/cpp/standard_library/16_localization/
// polyglot-related+: test_141_locale_objects_categories_facets_and_global_state.cpp

#include <gtest/gtest.h>

#include <iomanip>
#include <locale>
#include <sstream>
#include <string>

namespace {

TEST(LocaleConcept, StreamCanUseAnExplicitClassicLocale) {
  std::ostringstream output;
  output.imbue(std::locale::classic());
  output << std::fixed << std::setprecision(2) << 1234.5;

  EXPECT_EQ(output.str(), "1234.50");
}

TEST(LocaleConcept, CollateFacetDefinesLocaleSpecificComparison) {
  const std::locale locale = std::locale::classic();
  const auto& collate = std::use_facet<std::collate<char>>(locale);

  EXPECT_LT(collate.compare("a", "a" + 1, "b", "b" + 1), 0);
}

TEST(LocaleConcept, TimePutFormatsCalendarFieldsThroughAFacet) {
  std::tm value{};
  value.tm_year = 124;
  value.tm_mon = 0;
  value.tm_mday = 1;
  std::ostringstream output;
  output.imbue(std::locale::classic());
  output << std::put_time(&value, "%Y-%m-%d");

  EXPECT_EQ(output.str(), "2024-01-01");
}

TEST(LocaleConcept, LocaleAvailabilityIsImplementationAndHostDependent) {
  EXPECT_NO_THROW(static_cast<void>(std::locale::classic()));

  // 除 classic/C 外的命名区域依赖宿主安装，不以构造 en_US.UTF-8 失败来判断语言语义。
}

}  // namespace
