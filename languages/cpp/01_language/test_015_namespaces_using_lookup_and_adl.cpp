// polyglot-covers:
// - cpp.language.nested-inline-and-namespace-aliases
// - cpp.language.using-declarations-and-directives
// - cpp.language.using-enum
// - cpp.language.argument-dependent-lookup
// - cpp.language.hidden-friend
// - cpp.language.adl-swap-customization

#include <gtest/gtest.h>

#include <string>
#include <utility>

namespace library_api {

namespace v1 {
std::string version() { return "v1"; }
}

inline namespace v2 {
std::string version() { return "v2"; }
}

namespace detail::parsing {
int token_count() { return 3; }
}

}  // namespace library_api

namespace geometry {

struct Point {
  int x;
  int y;

  friend int manhattan_distance(const Point& point) {
    int horizontal = point.x < 0 ? -point.x : point.x;
    int vertical = point.y < 0 ? -point.y : point.y;
    return horizontal + vertical;
  }
};

}  // namespace geometry

namespace records {

inline int custom_swap_calls = 0;

struct Record {
  int value;
};

void swap(Record& left, Record& right) noexcept {
  ++custom_swap_calls;
  std::swap(left.value, right.value);
}

}  // namespace records

namespace {

enum class TrafficLight {
  red,
  amber,
  green,
};

TEST(Namespaces, InlineNamespaceProvidesTheDefaultVersion) {
  namespace api = library_api;

  EXPECT_EQ(api::version(), "v2");
  EXPECT_EQ(api::v1::version(), "v1");
  EXPECT_EQ(api::detail::parsing::token_count(), 3);

  // inline namespace 的成员也像外围命名空间成员一样可见，适合选择默认 ABI/API 版本；
  // 旧版本仍能通过限定名访问。namespace alias 只提供短名字，不创建新命名空间副本。
}

TEST(Namespaces, UsingDeclarationImportsOneNameWhileDirectiveAffectsLookup) {
  using library_api::v1::version;
  EXPECT_EQ(version(), "v1");

  {
    using namespace library_api::detail::parsing;
    EXPECT_EQ(token_count(), 3);
  }

  // using-declaration 把指定声明引入当前声明区域；using-directive 让普通查找考虑整个
  // 命名空间。头文件中的 directive 会污染所有包含者，应避免放在全局作用域。
}

TEST(Namespaces, UsingEnumImportsEnumeratorsWithoutImportingTheEnumType) {
  using enum TrafficLight;

  TrafficLight current = amber;
  EXPECT_EQ(current, TrafficLight::amber);

  // C++20 using enum 一次引入 scoped enum 的枚举器，适合局部 switch；枚举类型本身
  // 仍是 TrafficLight，枚举器也不会因此获得隐式整数转换。
}

TEST(Adl, AssociatedNamespaceFindsAHiddenFriend) {
  geometry::Point point{-3, 4};

  EXPECT_EQ(manhattan_distance(point), 7);

  // 普通非限定查找看不到类内定义且未在命名空间另行声明的 hidden friend；参数类型
  // Point 让 ADL 检查 geometry，因而找到它。没有类或枚举参数时不会发生这种查找。
}

TEST(Adl, TheUsingStdSwapPatternKeepsUserCustomizationAvailable) {
  records::custom_swap_calls = 0;
  records::Record first{1};
  records::Record second{2};

  using std::swap;
  swap(first, second);

  EXPECT_EQ(first.value, 2);
  EXPECT_EQ(second.value, 1);
  EXPECT_EQ(records::custom_swap_calls, 1);

  // 先把 std::swap 作为 fallback 引入，再做非限定调用，ADL 可选择类型命名空间中的
  // 更合适重载。直接写 std::swap(first, second) 会绕过这个经典自定义点。
}

}  // namespace
