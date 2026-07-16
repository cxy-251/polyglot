// polyglot-covers:
// - cpp.stdlib.meta.is-same-base-of-and-convertible
// - cpp.stdlib.meta.is-nothrow-convertible
// - cpp.stdlib.meta.invocable-and-invocable-r
// - cpp.stdlib.meta.nothrow-invocable
// - cpp.stdlib.meta.invoke-result
// - cpp.stdlib.meta.conjunction-disjunction-and-negation
// - cpp.stdlib.meta.logical-trait-short-circuiting
// - cpp.stdlib.meta.layout-compatible-and-corresponding-member
// - cpp.stdlib.meta.pointer-interconvertibility-traits
// - cpp.implementation.libstdcxx11-layout-compatibility-traits-gap
// - cpp.implementation.libstdcxx11-pointer-interconvertibility-traits-gap

#include <gtest/gtest.h>

#include <functional>
#include <string>
#include <string_view>
#include <type_traits>

namespace {

struct Root {};
struct LeftBranch : Root {};
struct RightBranch : Root {};
struct AmbiguousDiamond : LeftBranch, RightBranch {};

struct NoThrowInteger {
  operator int() const noexcept { return 7; }
};

struct ThrowingInteger {
  operator int() const noexcept(false) { return 9; }
};

class Calculator {
 public:
  int scale(int value) const noexcept { return factor_ * value; }
  std::string label() const { return "calculator"; }
  int factor_ = 3;
};

struct MissingValueMember {};

struct SourceLayout {
  int id;
  double score;
};

struct TargetLayout {
  int key;
  double value;
};

struct ReorderedLayout {
  double value;
  int key;
};

struct PacketHeader {
  int kind;
  int length;
};

template <typename Value>
constexpr const char* transfer_strategy() {
  if constexpr (
      std::is_nothrow_move_constructible_v<Value> ||
      !std::is_copy_constructible_v<Value>) {
    return "move";
  } else {
    return "copy";
  }
}

struct CopyableThrowingMove {
  CopyableThrowingMove() = default;
  CopyableThrowingMove(const CopyableThrowingMove&) = default;
  CopyableThrowingMove(CopyableThrowingMove&&) noexcept(false) {}
};

struct MoveOnlyThrowingMove {
  MoveOnlyThrowingMove() = default;
  MoveOnlyThrowingMove(const MoveOnlyThrowingMove&) = delete;
  MoveOnlyThrowingMove(MoveOnlyThrowingMove&&) noexcept(false) {}
};

TEST(TypeRelations, BaseOfDoesNotRequireAnAccessibleUnambiguousConversion) {
  static_assert(std::is_same_v<int, int>);
  static_assert(!std::is_same_v<int, const int>);
  static_assert(std::is_base_of_v<Root, AmbiguousDiamond>);
  static_assert(!std::is_convertible_v<AmbiguousDiamond*, Root*>);
  static_assert(std::is_convertible_v<LeftBranch*, Root*>);
  SUCCEED();

  // is_same 要求精确相同，不会忽略 cv 或做转换。is_base_of 只查继承图，
  // 即使 Root 在菱形中出现两次也为 true；真正的指针转换却因歧义而不可用。
}

TEST(TypeRelations, NothrowConvertibleAddsAnExceptionGuaranteeToConvertibility) {
  static_assert(std::is_convertible_v<NoThrowInteger, int>);
  static_assert(std::is_nothrow_convertible_v<NoThrowInteger, int>);
  static_assert(std::is_convertible_v<ThrowingInteger, int>);
  static_assert(!std::is_nothrow_convertible_v<ThrowingInteger, int>);

  EXPECT_EQ(static_cast<int>(NoThrowInteger{}), 7);
  EXPECT_EQ(static_cast<int>(ThrowingInteger{}), 9);

  // 两种转换都可编译，只有 noexcept conversion 满足 is_nothrow_convertible。
  // 依赖无抛出保证的泛型组件应查后者，不能把“这个案例没抛”当成类型契约。
}

TEST(CallableTraits, MemberPointersFollowInvokeRules) {
  using Scale = decltype(&Calculator::scale);
  using Factor = decltype(&Calculator::factor_);
  using Label = decltype(&Calculator::label);

  static_assert(std::is_invocable_v<Scale, const Calculator&, int>);
  static_assert(std::is_invocable_v<Scale, const Calculator*, int>);
  static_assert(std::is_invocable_v<Scale, std::reference_wrapper<Calculator>, int>);
  static_assert(std::is_invocable_r_v<long, Scale, const Calculator&, int>);
  static_assert(!std::is_invocable_r_v<int*, Scale, const Calculator&, int>);
  static_assert(std::is_invocable_v<Factor, Calculator&>);
  static_assert(std::is_invocable_r_v<std::string, Label, const Calculator&>);

  Calculator calculator;
  EXPECT_EQ(std::invoke(&Calculator::scale, calculator, 4), 12);
  EXPECT_EQ(std::invoke(&Calculator::factor_, calculator), 3);

  // invocable trait 使用与 std::invoke 相同的成员指针规则，会识别对象引用、
  // 指针和 reference_wrapper。is_invocable_r 还要求返回值能隐式转为 R；R 不是必须精确相同。
}

TEST(CallableTraits, InvokeResultAndNothrowQueriesDescribeTheSelectedCall) {
  using Scale = decltype(&Calculator::scale);
  using Label = decltype(&Calculator::label);
  using Result = std::invoke_result_t<Scale, const Calculator&, short>;

  static_assert(std::is_same_v<Result, int>);
  static_assert(std::is_nothrow_invocable_v<Scale, const Calculator&, int>);
  static_assert(
      std::is_nothrow_invocable_r_v<long, Scale, const Calculator&, int>);
  static_assert(!std::is_nothrow_invocable_v<Label, const Calculator&>);
  SUCCEED();

  // invoke_result 只在对应 INVOKE 表达式成立时提供 type；盲目访问无效调用的
  // ::type 会编译失败。先用 is_invocable 或 requires 筛选，再在有效分支提取结果。
}

TEST(LogicalTraits, ConjunctionAndDisjunctionShortCircuitInstantiation) {
  static_assert(!std::conjunction_v<std::false_type, MissingValueMember>);
  static_assert(std::disjunction_v<std::true_type, MissingValueMember>);
  static_assert(std::negation_v<std::false_type>);
  static_assert(std::conjunction_v<>);
  static_assert(!std::disjunction_v<>);
  SUCCEED();

  // conjunction 遇到第一个 false 就停止，disjunction 遇到第一个 true 就停止；
  // 因此 MissingValueMember 没有 value 也不会被实例化。这与先形成所有表达式的普通布尔 fold 不同。
}

TEST(LogicalTraits, CompositeConditionsCanDriveARealCompileTimePolicy) {
  static_assert(
      std::string_view{transfer_strategy<CopyableThrowingMove>()} == "copy");
  static_assert(
      std::string_view{transfer_strategy<MoveOnlyThrowingMove>()} == "move");
  static_assert(std::string_view{transfer_strategy<std::string>()} == "move");
  SUCCEED();

  // 类似 vector 重定位的策略常把多个 trait 组合：移动不抛时优先移动；
  // 移动可抛且可复制时为了异常保证选复制；若根本不可复制，则只能接受移动的风险。
}

TEST(LayoutRelations, CompareLayoutWithoutClaimingTheTypesAreIdentical) {
#ifdef __cpp_lib_is_layout_compatible
  static_assert(std::is_standard_layout_v<SourceLayout>);
  static_assert(std::is_standard_layout_v<TargetLayout>);
  static_assert(std::is_layout_compatible_v<SourceLayout, TargetLayout>);
  static_assert(!std::is_layout_compatible_v<SourceLayout, ReorderedLayout>);
  static_assert(
      std::is_corresponding_member(&SourceLayout::id, &TargetLayout::key));
  static_assert(
      std::is_corresponding_member(&SourceLayout::score, &TargetLayout::value));
  static_assert(
      !std::is_corresponding_member(&SourceLayout::id, &TargetLayout::value));
  SUCCEED();

  // layout-compatible 允许两个不同的 standard-layout 类型共享布局形状，
  // corresponding_member 进一步比较成员在 common initial sequence 中的位置。
#else
  // GCC 11.4 的 libstdc++ 未定义 __cpp_lib_is_layout_compatible，因此当前基线
  // 无法实例化 is_layout_compatible 和 is_corresponding_member。升级后会自动进入真实断言分支。
  GTEST_SKIP() << "libstdc++ lacks C++20 layout compatibility traits";
#endif
}

TEST(LayoutRelations, OnlyTheFirstMemberIsPointerInterconvertibleWithItsObject) {
#ifdef __cpp_lib_is_pointer_interconvertible
  static_assert(
      std::is_pointer_interconvertible_with_class(&PacketHeader::kind));
  static_assert(
      !std::is_pointer_interconvertible_with_class(&PacketHeader::length));

  PacketHeader packet{3, 128};
  EXPECT_EQ(reinterpret_cast<void*>(&packet), reinterpret_cast<void*>(&packet.kind));

  // standard-layout 对象与第一个非静态成员 pointer-interconvertible，可在两者
  // 地址间 reinterpret_cast。后续成员即使紧邻也不具有该语义；不要把相同数值地址泛化为可互换对象。
#else
  // GCC 11.4 的 libstdc++ 未定义 __cpp_lib_is_pointer_interconvertible，当前无法
  // 调用该 C++20 trait。保留条件分支而不用手写 offsetof 假装等价语义。
  GTEST_SKIP() << "libstdc++ lacks C++20 pointer interconvertibility traits";
#endif
}

}  // namespace
