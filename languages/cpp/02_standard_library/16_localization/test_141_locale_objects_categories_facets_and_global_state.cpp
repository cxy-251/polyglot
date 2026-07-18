// polyglot-covers:
// - cpp.stdlib.localization.locale-classic-named-default-and-invalid-construction
// - cpp.stdlib.localization.locale-category-masks-and-category-replacement
// - cpp.stdlib.localization.locale-named-category-composition
// - cpp.stdlib.localization.locale-custom-facet-id-has-and-use
// - cpp.stdlib.localization.locale-facet-reference-count-and-shared-lifetime
// - cpp.stdlib.localization.locale-combine-single-facet
// - cpp.stdlib.localization.locale-combine-unnamed-result-and-libstdcxx-gap
// - cpp.stdlib.localization.locale-name-equality-and-unnamed-composition
// - cpp.stdlib.localization.locale-collation-call-operator
// - cpp.stdlib.localization.locale-global-default-snapshot-and-restoration

#include <gtest/gtest.h>

#include <locale>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

namespace {

class LabelFacet : public std::locale::facet {
 public:
  static std::locale::id id;

  explicit LabelFacet(
      std::string label,
      int* destruction_count = nullptr,
      std::size_t references = 0)
      : std::locale::facet{references},
        label_{std::move(label)},
        destruction_count_{destruction_count} {}

  ~LabelFacet() override {
    if (destruction_count_ != nullptr) {
      ++*destruction_count_;
    }
  }

  [[nodiscard]] const std::string& label() const noexcept { return label_; }

 private:
  std::string label_;
  int* destruction_count_;
};

std::locale::id LabelFacet::id;

class MissingFacet : public std::locale::facet {
 public:
  static std::locale::id id;
};

std::locale::id MissingFacet::id;

class CommaNumpunct : public std::numpunct<char> {
 protected:
  char do_decimal_point() const override { return ','; }
};

class GlobalLocaleGuard {
 public:
  explicit GlobalLocaleGuard(const std::locale& replacement)
      : previous_{std::locale::global(replacement)} {}

  ~GlobalLocaleGuard() { std::locale::global(previous_); }

  GlobalLocaleGuard(const GlobalLocaleGuard&) = delete;
  GlobalLocaleGuard& operator=(const GlobalLocaleGuard&) = delete;

  [[nodiscard]] const std::locale& previous() const noexcept { return previous_; }

 private:
  std::locale previous_;
};

TEST(LocaleConstruction, ClassicNamedAndDefaultLocalesHaveDifferentSources) {
  const std::locale classic = std::locale::classic();
  const std::locale named_c{"C"};
  const std::locale current_default{};

  EXPECT_EQ(classic.name(), "C");
  EXPECT_EQ(named_c, classic);
  EXPECT_EQ(current_default.name(), std::locale{}.name());
  EXPECT_THROW(
      static_cast<void>(std::locale{"polyglot-locale-that-does-not-exist"}),
      std::runtime_error);

  // classic() 永远代表标准要求的最小 C locale；locale("C") 查询运行库的命名
  // locale；无参构造则复制当前 C++ 全局 locale。三者当前相等不代表来源相同。
}

TEST(LocaleCategories, MasksSelectGroupsOfStandardFacetsDuringComposition) {
  const std::locale classic = std::locale::classic();
  const std::locale comma{classic, new CommaNumpunct};
  const std::locale numeric_only{classic, comma, std::locale::numeric};
  const std::locale unchanged{comma, classic, std::locale::none};

  EXPECT_EQ(std::locale::none, 0);
  EXPECT_EQ(std::locale::all & std::locale::numeric, std::locale::numeric);
  EXPECT_NE(std::locale::numeric & std::locale::collate, std::locale::numeric);
  EXPECT_EQ(
      std::use_facet<std::numpunct<char>>(numeric_only).decimal_point(),
      ',');
  EXPECT_EQ(
      std::use_facet<std::ctype<char>>(numeric_only).toupper('a'),
      'A');
  EXPECT_FALSE(unchanged == comma);
  EXPECT_EQ(
      &std::use_facet<std::numpunct<char>>(unchanged),
      &std::use_facet<std::numpunct<char>>(comma));
  EXPECT_EQ(numeric_only.name(), "*");

  // category 是 facet 组的位掩码，不是单个 facet。numeric 会连同 num_get、
  // num_put、numpunct 等整组替换。即使 none 让 facet 身份完全相同，新构造的两个
  // 未命名 locale 也不因内容相同而相等；operator== 只认同一对象、复制或同名对象。
}

TEST(LocaleCategories, NamedCompositionReplacesOnlyTheSelectedStandardCategory) {
  const std::locale classic = std::locale::classic();
  const std::locale comma{classic, new CommaNumpunct};
  const std::locale numeric_from_c{comma, "C", std::locale::numeric};
  const std::locale named_from_c{classic, "C", std::locale::numeric};

  EXPECT_EQ(
      std::use_facet<std::numpunct<char>>(numeric_from_c).decimal_point(),
      '.');
  EXPECT_EQ(
      &std::use_facet<std::ctype<char>>(numeric_from_c),
      &std::use_facet<std::ctype<char>>(comma));
  EXPECT_EQ(numeric_from_c.name(), "*");
  EXPECT_EQ(named_from_c.name(), "C");
  EXPECT_EQ(named_from_c, classic);

  // locale(base, name, category) 从命名 locale 只取指定标准 facet 组，其他 facet
  // 保留 base 身份；结果是否有名字取决于 base 是否有名字，而不是替换来源是否有名字。
}

TEST(LocaleFacets, HasFacetChecksBeforeUseFacetAndIdsIdentifyFacetFamilies) {
  const std::locale classic = std::locale::classic();
  const std::locale labeled{classic, new LabelFacet{"zh-CN teaching label"}};

  EXPECT_FALSE(std::has_facet<LabelFacet>(classic));
  EXPECT_TRUE(std::has_facet<LabelFacet>(labeled));
  EXPECT_EQ(std::use_facet<LabelFacet>(labeled).label(), "zh-CN teaching label");
  EXPECT_THROW(
      static_cast<void>(std::use_facet<MissingFacet>(labeled)),
      std::bad_cast);

  // 每个 facet 类型用静态 locale::id 获得槽位。use_facet 返回由 locale 管理的
  // const 引用；缺失时抛 bad_cast，因此可选 facet 应先用 has_facet 探测。
}

TEST(LocaleFacetLifetime, LocaleCopiesShareOwnedFacetsUntilTheLastCopyDies) {
  int destruction_count = 0;
  {
    const std::locale first{
        std::locale::classic(),
        new LabelFacet{"shared", &destruction_count}};
    {
      const std::locale second = first;
      EXPECT_EQ(
          &std::use_facet<LabelFacet>(first),
          &std::use_facet<LabelFacet>(second));
      EXPECT_EQ(destruction_count, 0);
    }
    EXPECT_EQ(destruction_count, 0);
  }
  EXPECT_EQ(destruction_count, 1);

  // locale 是廉价、不可变且共享 facet 的句柄。refs=0 时最后一个引用负责销毁，
  // 复制 locale 不会复制 facet 对象，也不能缓存超过所有 locale 寿命的 facet 引用。
}

TEST(LocaleFacetLifetime, NonzeroReferenceCountLeavesFacetOwnershipWithTheCaller) {
  int destruction_count = 0;
  auto* borrowed = new LabelFacet{"borrowed", &destruction_count, 1};
  {
    const std::locale locale{std::locale::classic(), borrowed};
    EXPECT_EQ(std::use_facet<LabelFacet>(locale).label(), "borrowed");
  }
  EXPECT_EQ(destruction_count, 0);
  delete borrowed;
  EXPECT_EQ(destruction_count, 1);

  // facet 构造参数 refs 非零表示 locale 不接管销毁责任，并不表示传入一个真实的
  // 引用计数值。调用者必须保证对象覆盖所有使用它的 locale，通常更安全的是 refs=0。
}

TEST(LocaleCombination, CombineCopiesOneFacetWithoutReplacingItsWholeCategory) {
  const std::locale source{
      std::locale::classic(),
      new LabelFacet{"source facet"}};
  const std::locale combined = std::locale::classic().combine<LabelFacet>(source);

  EXPECT_EQ(std::use_facet<LabelFacet>(combined).label(), "source facet");
  EXPECT_EQ(
      std::use_facet<std::numpunct<char>>(combined).decimal_point(),
      '.');
  EXPECT_THROW(
      static_cast<void>(source.combine<MissingFacet>(std::locale::classic())),
      std::runtime_error);

  // combine<Facet> 只复制指定槽位，适合正交的应用 facet；category 构造函数替换
  // 整组标准 facet。与 use_facet 不同，来源缺少目标 facet 时标准要求 runtime_error。
}

TEST(LocaleCombination, StandardRequiresCombinedLocaleToLoseItsName) {
  const std::locale classic = std::locale::classic();
  const std::locale combined = classic.combine<std::ctype<char>>(classic);

  if (combined.name() != "*") {
    // N4861 [locale.members] 明定 combine 的结果无名称；libstdc++ PR108323
    // 于 GCC 15 开发周期修复旧实现仍保留来源名称的问题。
    GTEST_SKIP() << "libstdc++ 11 retains the locale name after combine (PR108323)";
  }
  EXPECT_EQ(combined.name(), "*");
}

TEST(LocaleComparison, NamedEqualityAndCollationAreDifferentOperations) {
  const std::locale classic = std::locale::classic();
  const std::locale named_c{"C"};
  const std::locale custom{classic, new LabelFacet{"custom"}};

  EXPECT_TRUE(classic == named_c);
  EXPECT_FALSE(classic == custom);
  EXPECT_TRUE(classic(std::string{"alpha"}, std::string{"beta"}));
  EXPECT_FALSE(classic(std::string{"beta"}, std::string{"alpha"}));

  // locale 的相等性比较 facet 身份/命名语义；operator() 则调用 collate facet，
  // 可直接作为有序容器比较器。它不等于逐字节 operator<，结果依赖所选 locale。
}

TEST(LocaleGlobalState, DefaultConstructionTakesASnapshotOfTheCurrentGlobalLocale) {
  const std::locale before{};
  {
    const GlobalLocaleGuard guard{std::locale::classic()};
    const std::locale first_snapshot{};
    const std::locale replacement{
        std::locale::classic(),
        new LabelFacet{"later replacement"}};

    EXPECT_EQ(guard.previous(), before);
    EXPECT_EQ(first_snapshot, std::locale::classic());
    std::locale::global(replacement);
    const std::locale second_snapshot{};
    EXPECT_FALSE(std::has_facet<LabelFacet>(first_snapshot));
    EXPECT_TRUE(std::has_facet<LabelFacet>(second_snapshot));
  }
  EXPECT_EQ(std::locale{}, before);

  // global() 返回旧值并影响以后无参构造的 locale；已经存在的对象不会变化。
  // 命名 locale 还可能同步 C locale，因此库代码应优先传递/imbue 显式对象并及时恢复。
}

}  // namespace
