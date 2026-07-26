// polyglot-covers:
// - cpp.stdlib.localization.collate-compare-transform-and-hash-contract
// - cpp.stdlib.localization.collate-custom-virtual-dispatch-and-equivalence
// - cpp.stdlib.localization.locale-call-operator-as-container-comparator
// - cpp.stdlib.localization.collate-byname-c-locale
// - cpp.stdlib.localization.collation-key-and-hash-persistence-traps
// - cpp.stdlib.localization.messages-open-get-close-catalog-lifetime
// - cpp.stdlib.localization.messages-default-fallback-and-custom-virtual-dispatch
// - cpp.stdlib.localization.messages-byname-and-implementation-defined-catalog-mapping

#include <gtest/gtest.h>

#include <algorithm>
#include <cstddef>
#include <locale>
#include <set>
#include <string>
#include <string_view>

namespace {

class AsciiCaseFoldCollate : public std::collate<char> {
 private:
  static std::string fold(const char* first, const char* last) {
    std::string result{first, last};
    std::transform(result.begin(), result.end(), result.begin(), [](char value) {
      if (value >= 'A' && value <= 'Z') {
        return static_cast<char>(value - 'A' + 'a');
      }
      return value;
    });
    return result;
  }

  int do_compare(
      const char* first_begin,
      const char* first_end,
      const char* second_begin,
      const char* second_end) const override {
    const std::string first = fold(first_begin, first_end);
    const std::string second = fold(second_begin, second_end);
    if (first < second) {
      return -1;
    }
    if (second < first) {
      return 1;
    }
    return 0;
  }

  std::string do_transform(const char* first, const char* last) const override {
    return fold(first, last);
  }

  long do_hash(const char* first, const char* last) const override {
    unsigned long value = 1469598103934665603UL;
    for (const unsigned char code_unit : fold(first, last)) {
      value ^= code_unit;
      value *= 1099511628211UL;
    }
    return static_cast<long>(value);
  }
};

class TeachingMessages : public std::messages<char> {
 public:
  [[nodiscard]] int close_count() const noexcept { return close_count_; }

 protected:
  catalog do_open(const std::string& name, const std::locale&) const override {
    return name == "polyglot-course" ? static_cast<catalog>(7)
                                      : static_cast<catalog>(-1);
  }

  std::string do_get(
      catalog opened,
      int set,
      int message,
      const std::string& fallback) const override {
    if (opened == static_cast<catalog>(7) && set == 1 && message == 10) {
      return "localized greeting";
    }
    return fallback;
  }

  void do_close(catalog opened) const override {
    if (opened == static_cast<catalog>(7)) {
      ++close_count_;
    }
  }

 private:
  mutable int close_count_ = 0;
};

TEST(CollateClassic, CompareTransformAndHashOperateOnExplicitRanges) {
  const auto& facet =
      std::use_facet<std::collate<char>>(std::locale::classic());
  const std::string alpha = "alpha";
  const std::string beta = "beta";

  EXPECT_LT(
      facet.compare(
          alpha.data(),
          alpha.data() + alpha.size(),
          beta.data(),
          beta.data() + beta.size()),
      0);
  EXPECT_EQ(
      facet.compare(
          alpha.data(),
          alpha.data() + alpha.size(),
          alpha.data(),
          alpha.data() + alpha.size()),
      0);
  EXPECT_LT(
      facet.transform(alpha.data(), alpha.data() + alpha.size()),
      facet.transform(beta.data(), beta.data() + beta.size()));
  EXPECT_EQ(
      facet.hash(alpha.data(), alpha.data() + alpha.size()),
      facet.hash(alpha.data(), alpha.data() + alpha.size()));

  // compare 只保证负、零、正的含义；transform 产生可重复比较的排序键，hash 只
  // 保证在该 facet 下比较相等的字符串哈希相等，并不承诺无碰撞。
}

TEST(CollateCustomization, VirtualFunctionsMustPreserveAllThreeEquivalenceContracts) {
  const std::locale folded{
      std::locale::classic(),
      new AsciiCaseFoldCollate};
  const auto& facet = std::use_facet<std::collate<char>>(folded);
  const std::string upper = "Alpha";
  const std::string lower = "alpha";

  EXPECT_EQ(
      facet.compare(
          upper.data(),
          upper.data() + upper.size(),
          lower.data(),
          lower.data() + lower.size()),
      0);
  EXPECT_EQ(
      facet.transform(upper.data(), upper.data() + upper.size()),
      facet.transform(lower.data(), lower.data() + lower.size()));
  EXPECT_EQ(
      facet.hash(upper.data(), upper.data() + upper.size()),
      facet.hash(lower.data(), lower.data() + lower.size()));

  // 自定义 compare 后必须同步 transform 与 hash 的等价关系，否则排序、缓存键和
  // 哈希容器会对“相等”产生冲突。本例只折叠 ASCII，不冒充完整 Unicode 大小写折叠。
}

TEST(LocaleComparator, CollationEquivalenceControlsOrderedContainerUniqueness) {
  const std::locale folded{
      std::locale::classic(),
      new AsciiCaseFoldCollate};
  std::set<std::string, std::locale> words{folded};

  EXPECT_TRUE(words.insert("Alpha").second);
  EXPECT_FALSE(words.insert("alpha").second);
  EXPECT_TRUE(words.insert("beta").second);
  EXPECT_EQ(words.size(), 2U);

  // locale::operator() 直接满足比较器接口；容器唯一性由排序等价而非 operator==
  // 决定。切换 locale 意味着改变容器不变量，不能原地更换比较器后保留旧树结构。
}

TEST(CollateByName, NamedCFacetMatchesClassicBytewiseOrderingForAscii) {
  const std::locale named{
      std::locale::classic(),
      new std::collate_byname<char>{"C"}};
  const auto& facet = std::use_facet<std::collate<char>>(named);
  const std::string upper = "Z";
  const std::string lower = "a";

  EXPECT_LT(
      facet.compare(
          upper.data(),
          upper.data() + upper.size(),
          lower.data(),
          lower.data() + lower.size()),
      0);

  // 命名 locale 的排序规则可能随系统数据库版本变化。transform 键与 hash 值只应
  // 在同一 facet 生命周期内加速比较，不应作为跨机器、跨升级的持久化格式。
}

TEST(MessageCatalogFacet, OpenGetFallbackAndCloseFormAResourceProtocol) {
  const std::locale locale{
      std::locale::classic(),
      new TeachingMessages};
  const auto& messages = std::use_facet<std::messages<char>>(locale);
  const auto opened = messages.open("polyglot-course", locale);

  ASSERT_GE(opened, 0);
  EXPECT_EQ(messages.get(opened, 1, 10, "fallback"), "localized greeting");
  EXPECT_EQ(messages.get(opened, 1, 99, "fallback"), "fallback");
  messages.close(opened);

  const auto& teaching = static_cast<const TeachingMessages&>(messages);
  EXPECT_EQ(teaching.close_count(), 1);

  // catalog 是只能由 open 获得的未指定有符号整数句柄；成功后在 close 前有效。
  // get 找不到集合/消息时返回调用者默认值，默认值是正常回退路径而非异常。
}

TEST(MessageCatalogFacet, OpenFailureReturnsANegativeHandleThatMustNotBeUsed) {
  const std::locale locale{
      std::locale::classic(),
      new TeachingMessages};
  const auto& messages = std::use_facet<std::messages<char>>(locale);

  EXPECT_LT(messages.open("missing-catalog", locale), 0);

  // 标准只规定失败句柄小于零；把失败值传给 get/close 违反前置条件。真实代码应
  // 先检查 open，而不是假设 catalog 0 一定成功或 -1 是唯一失败值。
}

TEST(MessagesByName, FacetAvailabilityDoesNotMakeCatalogFormatsPortable) {
  const std::locale named{
      std::locale::classic(),
      new std::messages_byname<char>{"C"}};

  EXPECT_TRUE(std::has_facet<std::messages<char>>(named));

  // messages_byname("C") facet 本身可构造，但 catalog 名到文件/资源的映射、文件
  // 格式、字符集转换和资源上限均由实现定义，所以测试不依赖宿主机消息目录。
}

}  // namespace
