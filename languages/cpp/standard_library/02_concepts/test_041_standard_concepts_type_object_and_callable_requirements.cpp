// polyglot-covers:
// - cpp.stdlib.concepts.same-as-derived-from-and-convertible-to
// - cpp.stdlib.concepts.common-reference-with-and-common-with
// - cpp.stdlib.concepts.integral-signed-unsigned-and-floating-point
// - cpp.stdlib.concepts.assignable-from-and-swappable
// - cpp.stdlib.concepts.destructible-and-constructible-concepts
// - cpp.stdlib.concepts.equality-comparable-and-totally-ordered
// - cpp.stdlib.concepts.invocable-regular-invocable-and-predicate
// - cpp.stdlib.concepts.relation-equivalence-and-strict-weak-order

#include <gtest/gtest.h>

#include <concepts>
#include <functional>
#include <memory>
#include <string>
#include <type_traits>
#include <utility>

namespace {

struct Base {};
struct PublicDerived : Base {};
struct PrivateDerived : private Base {};

class ExplicitInteger {
 public:
  explicit ExplicitInteger(int value) : value_(value) {}
  explicit operator int() const { return value_; }

 private:
  int value_;
};

struct NoDefault {
  explicit NoDefault(int value) : value(value) {}
  int value;
};

struct MoveOnly {
  MoveOnly() = default;
  MoveOnly(const MoveOnly&) = delete;
  MoveOnly& operator=(const MoveOnly&) = delete;
  MoveOnly(MoveOnly&&) = default;
  MoveOnly& operator=(MoveOnly&&) = default;
};

namespace adl_swap_example {

struct Record {
  int value;
  int* swaps;

  friend void swap(Record& left, Record& right) noexcept {
    using std::swap;
    swap(left.value, right.value);
    ++*left.swaps;
  }
};

}  // namespace adl_swap_example

struct BadEquality {
  int value;

  friend bool operator==(const BadEquality&, const BadEquality&) {
    return false;
  }
};

TEST(TypeRelationships, SameAsIsSymmetricAndDerivedFromRequiresAccessibleConversion) {
  static_assert(std::same_as<int, int>);
  static_assert(!std::same_as<int, const int>);
  static_assert(std::derived_from<PublicDerived, Base>);

  static_assert(std::is_base_of_v<Base, PrivateDerived>);
  static_assert(!std::derived_from<PrivateDerived, Base>);

  // derived_from 不只问“Base 是否出现在继承图中”，还要求 public 且无歧义的派生到基类
  // 指针转换。is_base_of 对 private 继承仍为 true，两者不能在接口约束中随意互换。
}

TEST(TypeRelationships, ConvertibleToRequiresImplicitAndExplicitFormsToAgree) {
  static_assert(std::convertible_to<int, double>);
  static_assert(!std::convertible_to<ExplicitInteger, int>);
  static_assert(std::constructible_from<int, ExplicitInteger>);

  const ExplicitInteger value{7};
  EXPECT_EQ(static_cast<int>(value), 7);

  // convertible_to 同时要求隐式返回转换和 static_cast 都合法并具有相同结果；只有 explicit
  // 转换的类型不满足它。若 API 只需显式构造，应使用 constructible_from 表达真实需求。
}

TEST(CommonTypes, CommonReferenceAndCommonTypeDescribeDifferentMeetingPoints) {
  static_assert(std::common_reference_with<int&, const int&>);
  static_assert(std::same_as<std::common_reference_t<int&, const int&>, const int&>);
  static_assert(std::common_with<int, double>);
  static_assert(std::same_as<std::common_type_t<int, double>, double>);

  // common_reference_with 关注保留引用语义的共同引用；common_with 还要求 common_type 的
  // 对称性和相关转换。泛型算法若要写回对象，不能只把所有输入衰减成 common_type。
}

TEST(ArithmeticConcepts, BoolIsIntegralAndAlsoMeetsUnsignedIntegralDefinition) {
  static_assert(std::integral<int>);
  static_assert(std::signed_integral<int>);
  static_assert(std::unsigned_integral<unsigned int>);
  static_assert(std::floating_point<double>);

  static_assert(std::integral<bool>);
  static_assert(!std::signed_integral<bool>);
  static_assert(std::unsigned_integral<bool>);

  // unsigned_integral 定义为 integral 且非 signed_integral，所以 bool 也满足。若算法需要
  // 可计数的无符号整数，应额外排除 bool，不能把 concept 名称当作领域语义保证。
}

TEST(ObjectConcepts, AssignableFromModelsAssignmentToAnLvalue) {
  static_assert(std::assignable_from<int&, int>);
  static_assert(std::assignable_from<std::string&, const char*>);
  static_assert(!std::assignable_from<int, int>);

  int value = 1;
  int& result = (value = 9);
  EXPECT_EQ(&result, &value);

  // assignable_from 的左侧必须是 lvalue reference，并要求赋值表达式返回同一个左侧引用。
  // 普通类型 int 不是可赋值“目标表达式”；concept 约束的是操作形状而非类型有无 operator=。
}

TEST(ObjectConcepts, SwappableUsesRangesSwapAndKeepsAdlCustomization) {
  static_assert(std::swappable<adl_swap_example::Record>);
  static_assert(std::swappable_with<int&, int&>);

  int swap_count = 0;
  adl_swap_example::Record left{1, &swap_count};
  adl_swap_example::Record right{2, &swap_count};

  std::ranges::swap(left, right);
  EXPECT_EQ(left.value, 2);
  EXPECT_EQ(right.value, 1);
  EXPECT_EQ(swap_count, 1);

  // swappable 以 ranges::swap 的定制规则检查 ADL swap、数组和 move fallback。定制 swap
  // 应与移动交换结果一致并满足 noexcept 承诺，否则依赖交换的容器异常保证会受影响。
}

TEST(ObjectConcepts, ConstructionConceptsFormAUsefulCapabilityLattice) {
  static_assert(std::destructible<NoDefault>);
  static_assert(!std::default_initializable<NoDefault>);
  static_assert(std::constructible_from<NoDefault, int>);

  static_assert(std::movable<MoveOnly>);
  static_assert(!std::copyable<MoveOnly>);
  static_assert(std::move_constructible<std::unique_ptr<int>>);
  static_assert(!std::copy_constructible<std::unique_ptr<int>>);

  // movable 还要求对象可 move-assign 和 swappable，不等同于只有 move constructor。
  // copyable 进一步要求多种 const/非 const 复制形式；应选最小真实能力，避免过度约束 API。
}

TEST(ComparisonConcepts, SyntaxChecksCannotProveEqualitySemantics) {
  static_assert(std::equality_comparable<BadEquality>);
  static_assert(std::totally_ordered<int>);

  const BadEquality object{1};
  EXPECT_FALSE(object == object);

  // equality_comparable 的语义要求包含自反、对称、传递和 equality-preserving，但编译器
  // 只检查表达式与返回类型。这个故意撒谎的 == 仍通过 concept，责任仍在类型作者。
}

TEST(CallableConcepts, InvocablePredicateAndRelationsLayerAdditionalContracts) {
  const auto positive = [](int value) { return value > 0; };
  const auto compare = std::less<int>{};

  static_assert(std::invocable<decltype(positive), int>);
  static_assert(std::regular_invocable<decltype(positive), int>);
  static_assert(std::predicate<decltype(positive), int>);
  static_assert(std::relation<decltype(compare), int, int>);
  static_assert(std::equivalence_relation<std::equal_to<int>, int, int>);
  static_assert(std::strict_weak_order<decltype(compare), int, int>);

  EXPECT_TRUE(std::invoke(positive, 3));
  EXPECT_FALSE(std::invoke(positive, -1));

  // regular_invocable 与 invocable 的可编译检查相同，但前者还要求调用不修改函数对象或
  // 实参且 equality-preserving；predicate/relation 再增加布尔测试和数学关系契约。
}

TEST(CallableConcepts, StatefulCallablesMayPassSyntaxButViolateRegularSemantics) {
  auto counter = [calls = 0]() mutable { return ++calls; };

  static_assert(std::invocable<decltype(counter)&>);
  static_assert(std::regular_invocable<decltype(counter)&>);
  EXPECT_EQ(counter(), 1);
  EXPECT_EQ(counter(), 2);

  // regular_invocable 的状态不变和 equality-preserving 是不可由编译器普遍验证的语义要求。
  // 可变计数器虽在实现层面通过 concept，却不满足该语义，不能用于依赖重复结果的算法。
}

}  // namespace
