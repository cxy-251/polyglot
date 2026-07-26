// polyglot-covers:
// - cpp.language.fundamental-types
// - cpp.language.object-and-value
// - cpp.language.default-value-and-zero-initialization
// - cpp.language.direct-copy-and-list-initialization
// - cpp.language.aggregate-and-designated-initialization
// - cpp.language.initializer-list-overload-preference
// - cpp.language.most-vexing-parse

#include <gtest/gtest.h>

#include <array>
#include <climits>
#include <cstddef>
#include <initializer_list>
#include <limits>
#include <string>
#include <type_traits>
#include <utility>

namespace {

template <typename Target, typename Source>
concept ListInitializableFrom = requires(Source value) { Target{value}; };

struct PlainRecord {
  int count;
  double ratio;
};

struct RecordWithDefaults {
  int count{7};
  std::string label{"默认值"};
};

struct DesignatedRecord {
  int id;
  std::string name;
  bool enabled{true};
};

enum class ConstructionRoute {
  ordinary_arguments,
  initializer_list,
};

class InitializerChoice {
 public:
  InitializerChoice(int count, int value)
      : route_(ConstructionRoute::ordinary_arguments), values_(count, value) {}

  InitializerChoice(std::initializer_list<char> values)
      : route_(ConstructionRoute::initializer_list), values_(values) {}

  [[nodiscard]] ConstructionRoute route() const { return route_; }
  [[nodiscard]] const std::string& values() const { return values_; }

 private:
  ConstructionRoute route_;
  std::string values_;
};

struct EmptyMarker {};

// `EmptyMarker value();` 会把 value 声明成这种函数类型，而不是创建默认构造的对象。
// 这就是 most vexing parse：编译器优先按声明解释能够成为声明的语句。
using LooksLikeAnObject = EmptyMarker();

std::string select_null_overload(int*) { return "pointer"; }
std::string select_null_overload(int) { return "integer"; }

TEST(FundamentalTypes, TypeTraitsExposeTheStandardCategories) {
  static_assert(std::is_fundamental_v<int>);
  static_assert(std::is_fundamental_v<double>);
  static_assert(std::is_fundamental_v<void>);
  static_assert(std::is_fundamental_v<std::nullptr_t>);

  static_assert(std::is_integral_v<bool>);
  static_assert(std::is_integral_v<char>);
  static_assert(std::is_floating_point_v<long double>);

  // std::byte 用于表达“原始字节”，但它是枚举类而不是整数类型，因此不会意外参与算术。
  static_assert(std::is_enum_v<std::byte>);
  static_assert(!std::is_integral_v<std::byte>);
  EXPECT_EQ(std::to_integer<unsigned int>(std::byte{0x2A}), 42U);
}

TEST(FundamentalTypes, IntegerWidthsContainImplementationDefinedParts) {
  // 标准只保证 sizeof(char) == 1；这个“1”是一个字节，不保证等于八个 bit。
  EXPECT_EQ(sizeof(char), 1U);
  EXPECT_GE(CHAR_BIT, 8);

  EXPECT_LE(sizeof(char), sizeof(short));
  EXPECT_LE(sizeof(short), sizeof(int));
  EXPECT_LE(sizeof(int), sizeof(long));
  EXPECT_LE(sizeof(long), sizeof(long long));

  // 有符号类型至少提供负值、零和正值；具体位宽应通过 numeric_limits 查询，
  // 不能把常见的 32 位 int 当成语言保证。
  EXPECT_LT(std::numeric_limits<int>::lowest(), 0);
  EXPECT_EQ(std::numeric_limits<unsigned int>::lowest(), 0U);
  EXPECT_GT(std::numeric_limits<unsigned int>::max(), 0U);
}

TEST(FundamentalTypes, CharacterTypesAreDistinctEvenWhenRepresentationsMatch) {
  static_assert(!std::is_same_v<char, signed char>);
  static_assert(!std::is_same_v<char, unsigned char>);
  static_assert(!std::is_same_v<wchar_t, char16_t>);
  static_assert(!std::is_same_v<char16_t, char32_t>);

  // C++20 的 u8 字面量元素类型是 char8_t，不再是 char。decltype 对字符串字面量
  // 得到数组的左值引用，移除引用后仍可看到结尾零字符占用的第三个元素。
  using Utf8Literal = std::remove_reference_t<decltype(u8"hi")>;
  static_assert(std::is_same_v<Utf8Literal, const char8_t[3]>);

  // plain char 的 signedness 由实现决定；需要处理原始数值时应明确选 signed char 或
  // unsigned char，而不是根据本机结果推断所有平台。
  char converted = static_cast<char>(-1);
  if constexpr (std::numeric_limits<char>::is_signed) {
    EXPECT_LT(converted, 0);
  } else {
    EXPECT_GT(converted, 0);
  }
}

TEST(FundamentalTypes, NullptrHasPointerSemanticsWithoutBeingAnInteger) {
  static_assert(std::is_same_v<decltype(nullptr), std::nullptr_t>);
  static_assert(!std::is_integral_v<std::nullptr_t>);
  static_assert(std::is_convertible_v<std::nullptr_t, int*>);
  static_assert(!std::is_convertible_v<std::nullptr_t, int>);

  EXPECT_EQ(select_null_overload(nullptr), "pointer");
  EXPECT_EQ(select_null_overload(0), "integer");

  // 数字 0 仍可作为历史遗留的空指针常量，但它首先是 int。nullptr 能让重载解析
  // 清楚表达指针意图，也不会像实现相关的 NULL 宏那样意外选择整数重载。
}

TEST(Initialization, ValueInitializationZerosScalarMembers) {
  PlainRecord value_initialized{};
  EXPECT_EQ(value_initialized.count, 0);
  EXPECT_EQ(value_initialized.ratio, 0.0);

  std::array<int, 3> zeroed_array{};
  EXPECT_EQ(zeroed_array, (std::array<int, 3>{0, 0, 0}));

  PlainRecord default_initialized;
  // 上面的 default-initialization 不会初始化两个标量成员；读取它们会产生未定义行为。
  // 测试只能先赋值再读取，不能为了“证明未初始化”而执行一次非法读取。
  default_initialized.count = 9;
  default_initialized.ratio = 0.5;
  EXPECT_EQ(default_initialized.count, 9);
  EXPECT_EQ(default_initialized.ratio, 0.5);
}

TEST(Initialization, DefaultMemberInitializersParticipateInValueInitialization) {
  RecordWithDefaults record{};
  EXPECT_EQ(record.count, 7);
  EXPECT_EQ(record.label, "默认值");

  // 聚合初始化只提供前面的成员时，剩余成员先使用 default member initializer；
  // 没有类内默认值的剩余成员才按空列表进行初始化。
  RecordWithDefaults overridden{12};
  EXPECT_EQ(overridden.count, 12);
  EXPECT_EQ(overridden.label, "默认值");
}

TEST(Initialization, CopyDirectAndListFormsHaveDifferentSafetyRules) {
  int copy_initialized = 42;
  int direct_initialized(42);
  int list_initialized{42};

  EXPECT_EQ(copy_initialized, direct_initialized);
  EXPECT_EQ(direct_initialized, list_initialized);

  static_assert(ListInitializableFrom<int, int>);
  static_assert(!ListInitializableFrom<int, double>);

  // int value = 3.5 和 int value(3.5) 会执行截断转换，而 int value{3.5} 在编译期
  // 直接拒绝窄化。requires 表达式可以验证“是否能这样初始化”而不故意破坏整个构建。
  double source = 3.5;
  int explicit_conversion{static_cast<int>(source)};
  EXPECT_EQ(explicit_conversion, 3);
}

TEST(Initialization, AutoWithBracesHasTwoDifferentDeductionRules) {
  auto scalar{1};
  auto list = {1};

  static_assert(std::is_same_v<decltype(scalar), int>);
  static_assert(std::is_same_v<decltype(list), std::initializer_list<int>>);
  EXPECT_EQ(scalar, 1);
  EXPECT_EQ(list.size(), 1U);

  // auto value{1, 2} 非法，因为直接列表初始化的 auto 必须只有一个元素；
  // auto value = {1, 2} 则尝试推导共同元素类型的 initializer_list。
}

TEST(Initialization, AggregatesSupportOrderedDesignatorsInCpp20) {
  DesignatedRecord record{
      .id = 7,
      .name = "worker",
  };

  EXPECT_EQ(record.id, 7);
  EXPECT_EQ(record.name, "worker");
  EXPECT_TRUE(record.enabled);

  // C++20 指定初始化器必须遵守成员声明顺序，并且不能和位置初始化器混用；
  // 这与某些 C 编译器接受的扩展不同。省略的 enabled 仍使用类内默认值。
}

TEST(Initialization, InitializerListConstructorsWinForBraceSyntax) {
  InitializerChoice parentheses(3, 'x');
  InitializerChoice braces{3, 'x'};

  EXPECT_EQ(parentheses.route(), ConstructionRoute::ordinary_arguments);
  EXPECT_EQ(parentheses.values(), "xxx");

  EXPECT_EQ(braces.route(), ConstructionRoute::initializer_list);
  ASSERT_EQ(braces.values().size(), 2U);
  EXPECT_EQ(braces.values()[0], static_cast<char>(3));
  EXPECT_EQ(braces.values()[1], 'x');

  // 列表构造函数在重载解析中有优先阶段。花括号不只是括号的安全写法替代品；
  // 对容器等同时提供“数量/值”和 initializer_list 构造函数的类型，两者语义常不同。
}

TEST(Initialization, EmptyBracesAvoidTheMostVexingParse) {
  static_assert(std::is_function_v<LooksLikeAnObject>);

  EmptyMarker actual_object{};
  static_assert(std::is_same_v<decltype(actual_object), EmptyMarker>);
  SUCCEED();
}

}  // namespace
