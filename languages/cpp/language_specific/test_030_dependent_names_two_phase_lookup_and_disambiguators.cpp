// polyglot-covers:
// - cpp.language.dependent-name
// - cpp.language.typename-disambiguator
// - cpp.language.template-disambiguator
// - cpp.language.two-phase-lookup
// - cpp.language.dependent-base-member-lookup
// - cpp.language.argument-dependent-lookup-at-instantiation

#include <gtest/gtest.h>

#include <string>
#include <type_traits>
#include <vector>

namespace lookup_library {

template <typename Value>
std::string describe(const Value&) {
  return "generic";
}

template <typename Value>
std::string describe_through_template(const Value& value) {
  return describe(value);
}

}  // namespace lookup_library

namespace domain_model {

struct Widget {};

std::string describe(const Widget&) { return "domain widget"; }

}  // namespace domain_model

namespace lookup_library {

// 此重载晚于模板定义。它不在模板定义点的 ordinary lookup 结果中；int 也没有关联
// namespace 可供 ADL 在实例化点补充，因此模板调用仍选择早先可见的 generic 版本。
std::string describe(int) { return "late integer"; }

}  // namespace lookup_library

namespace {

template <typename Container>
typename Container::value_type first_value(const Container& values) {
  return values.front();
}

struct Converter {
  template <typename Result>
  Result convert() const {
    return Result{42};
  }
};

template <typename Value>
int call_dependent_member_template(const Value& value) {
  return value.template convert<int>();
}

template <typename Value>
struct Base {
  int inherited_value = 17;
};

template <typename Value>
struct Derived : Base<Value> {
  int read() const {
    return this->inherited_value;
  }
};

template <typename Value>
struct Traits {
  using item_type = Value;
  static constexpr int rank = 1;
};

template <typename Value>
struct Traits<Value*> {
  using item_type = Value;
  static constexpr int rank = 2;
};

template <typename Value>
auto trait_rank_and_default() {
  using Item = typename Traits<Value>::item_type;
  return std::pair{Traits<Value>::rank, Item{}};
}

TEST(DependentNames, TypenameMarksADependentQualifiedNameAsAType) {
  const std::vector<std::string> values{"first", "second"};
  EXPECT_EQ(first_value(values), "first");

  using Item = typename Traits<long*>::item_type;
  static_assert(std::is_same_v<Item, long>);

  // 解析模板定义时，编译器不知道 Container::value_type 是类型还是静态成员。typename
  // 消除语法歧义；基类列表和 using alias 的某些类型上下文则可隐式判定为类型。
}

TEST(DependentNames, TemplateKeywordDisambiguatesLessThanFromTemplateArguments) {
  EXPECT_EQ(call_dependent_member_template(Converter{}), 42);

  // value 的类型依赖模板参数，因此解析器不能预先知道 convert 是成员模板。template
  // 告诉它后面的 < 是模板实参列表，而不是小于运算符。
}

TEST(TwoPhaseLookup, DefinitionPointOrdinaryLookupAndInstantiationAdlWorkTogether) {
  EXPECT_EQ(
      lookup_library::describe_through_template(domain_model::Widget{}),
      "domain widget");
  EXPECT_EQ(lookup_library::describe_through_template(7), "generic");
  EXPECT_EQ(lookup_library::describe(7), "late integer");

  // 非依赖名在模板定义时绑定；依赖调用先保留定义点 ordinary lookup 的候选，再在实例化
  // 时从实参关联 namespace 做 ADL。不能靠“稍后在同一 namespace 添加重载”定制模板。
}

TEST(DependentBases, ThisMakesLookupWaitUntilTheBaseSpecializationIsKnown) {
  const Derived<int> value{};
  EXPECT_EQ(value.read(), 17);

  // dependent base 的成员不会参加模板定义点的非限定查找。写 this-> 或 Base<T>:: 可把
  // 名称标成 dependent，等实例化确定具体基类后再查找。
}

TEST(DependentSpecialization, MembersMayChangeWithTheSelectedSpecialization) {
  const auto [value_rank, value] = trait_rank_and_default<int>();
  const auto [pointer_rank, pointed] = trait_rank_and_default<int*>();

  EXPECT_EQ(value_rank, 1);
  EXPECT_EQ(pointer_rank, 2);
  EXPECT_EQ(value, 0);
  EXPECT_EQ(pointed, 0);

  // Traits<Value> 是 dependent specialization；其 item_type 和 rank 到实例化时才能由
  // primary 或 partial specialization 决定，这也是依赖名必须延迟检查的根本原因。
}

}  // namespace
