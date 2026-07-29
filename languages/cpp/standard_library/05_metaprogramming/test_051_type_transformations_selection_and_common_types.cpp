// polyglot-covers:
// - cpp.stdlib.meta.cv-reference-sign-array-and-pointer-transformations
// - cpp.stdlib.meta.remove-cvref-versus-decay
// - cpp.stdlib.meta.type-identity-nondeduced-context
// - cpp.stdlib.meta.conditional-and-enable-if
// - cpp.stdlib.meta.common-type-and-common-reference
// - cpp.stdlib.meta.underlying-type
// - cpp.stdlib.meta.unwrap-reference-and-unwrap-ref-decay
// - cpp.stdlib.meta.void-t-detection
// - cpp.stdlib.meta.aligned-storage-and-aligned-union
// - cpp.stdlib.meta.is-constant-evaluated

#include <gtest/gtest.h>

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <type_traits>

namespace {

enum class Permission : unsigned short {
  read = 1,
  write = 2,
};

int parse_number(const char*) { return 0; }

template <typename Value>
Value add_with_conversion(Value left, std::type_identity_t<Value> right) {
  return left + right;
}

template <typename Value, typename = void>
struct HasValueType : std::false_type {};

template <typename Value>
struct HasValueType<Value, std::void_t<typename Value::value_type>>
    : std::true_type {};

struct WithValueType {
  using value_type = long;
};

struct WithoutValueType {};

constexpr int evaluation_context() {
  return std::is_constant_evaluated() ? 1 : 2;
}

TEST(CvAndReferenceTransformations, OnlyTopLevelQualifiersAreChanged) {
  static_assert(std::is_same_v<std::remove_cv_t<const volatile int>, int>);
  static_assert(std::is_same_v<std::add_cv_t<int>, const volatile int>);
  static_assert(std::is_same_v<std::remove_cv_t<const int*>, const int*>);
  static_assert(std::is_same_v<std::remove_cv_t<int* const>, int*>);

  static_assert(std::is_same_v<std::remove_reference_t<int&&>, int>);
  static_assert(std::is_same_v<std::add_lvalue_reference_t<int>, int&>);
  static_assert(std::is_same_v<std::add_rvalue_reference_t<int>, int&&>);
  static_assert(std::is_same_v<std::add_rvalue_reference_t<int&>, int&>);
  static_assert(std::is_same_v<std::add_const_t<int&>, int&>);

  // remove_cv 只移除顶层 cv：const int* 的 const 修饰所指对象，不会被移除；
  // int* const 的 const 修饰指针本身。对引用 add_const 无效，add_rvalue_reference
  // 也会遵守引用折叠，不能靠 trait 强行把 T& 变成 T&&。
}

TEST(SignAndEnumTransformations, SignChangesPreserveRankAndCvQualification) {
  static_assert(
      std::is_same_v<std::make_unsigned_t<const int>, const unsigned int>);
  static_assert(
      std::is_same_v<std::make_signed_t<unsigned char>, signed char>);
  static_assert(
      std::is_same_v<std::underlying_type_t<Permission>, unsigned short>);

  constexpr auto bits = static_cast<std::underlying_type_t<Permission>>(
      Permission::write);
  EXPECT_EQ(bits, 2);

  // make_signed/make_unsigned 保留整数 rank 和顶层 cv；bool 不满足它们的前置条件。
  // scoped enum 不会隐式转为整数，underlying_type 只提取存储类型，仍需显式 cast。
}

TEST(ArrayAndPointerTransformations, EachTraitChangesOneDeclaratorLayer) {
  using Matrix = const int[2][3];

  static_assert(std::is_same_v<std::remove_extent_t<Matrix>, const int[3]>);
  static_assert(std::is_same_v<std::remove_all_extents_t<Matrix>, const int>);
  static_assert(std::is_same_v<std::remove_pointer_t<const int* const>, const int>);
  static_assert(std::is_same_v<std::add_pointer_t<int&>, int*>);
  static_assert(std::is_same_v<std::add_pointer_t<void>, void*>);

  // remove_extent 只剔除最外层数组，remove_all_extents 才递归到元素类型。
  // remove_pointer 同时去掉指针自身的 cv，但保留 pointee 的 const。这些 trait
  // 是类型语法变换，不分配存储，也不改变任何现有对象。
}

TEST(Decay, ArraysAndFunctionsLoseShapeWhileRemoveCvrefPreservesIt) {
  using ArrayReference = const int (&)[4];
  using FunctionReference = int (&)(const char*);

  static_assert(std::is_same_v<std::remove_cvref_t<ArrayReference>, int[4]>);
  static_assert(std::is_same_v<std::decay_t<ArrayReference>, const int*>);
  static_assert(
      std::is_same_v<std::remove_cvref_t<FunctionReference>, int(const char*)>);
  static_assert(
      std::is_same_v<std::decay_t<FunctionReference>, int (*)(const char*)>);
  static_assert(std::is_same_v<decltype(&parse_number), int (*)(const char*)>);

  // remove_cvref 只移除引用和顶层 cv，所以保留数组长度与函数签名。decay
  // 模拟按值传参：数组变指针、函数变函数指针，其他类型再移除 cvref。
}

TEST(TypeIdentity, MakesAFunctionParameterANondeducedContext) {
  const double sum = add_with_conversion(1.5, 2);
  EXPECT_DOUBLE_EQ(sum, 3.5);

  // Value 只从第一个实参推导为 double，type_identity_t<Value> 是不推导语境，
  // 所以第二个 int 随后正常转为 double。若两个参数都写 Value，1.5 和 2 会导致
  // 推导冲突，而不是先选 double 再转换。
}

TEST(SelectionTraits, ConditionalAndEnableIfProduceTypesRatherThanValues) {
  using Identifier =
      std::conditional_t<(sizeof(void*) > sizeof(std::uint32_t)), std::uint64_t, std::uint32_t>;
  using Enabled = std::enable_if_t<std::is_integral_v<Identifier>, Identifier>;

  static_assert(std::is_same_v<Enabled, Identifier>);
  static_assert(sizeof(Identifier) >= sizeof(std::uint32_t));

  // conditional 在两个已给定的类型中选一个；enable_if<false> 则根本没有 type。
  // 后者适合 SFINAE 接口兼容，C++20 新代码的可读性通常优先 requires/concept。
}

TEST(CommonTypes, ValueAndReferenceMeetingPointsServeDifferentAlgorithms) {
  using ValueCommon = std::common_type_t<int, const double&, short>;
  using ReferenceCommon = std::common_reference_t<int&, const int&>;

  static_assert(std::is_same_v<ValueCommon, double>);
  static_assert(std::is_same_v<ReferenceCommon, const int&>);
  static_assert(std::is_convertible_v<int&, ReferenceCommon>);
  static_assert(std::is_convertible_v<const int&, ReferenceCommon>);

  // common_type 通常经过 decay，适合产生一个独立结果值；common_reference 尝试
  // 保留可共享的引用语义。泛型算法需要写回输入时，不能一律用 common_type。
}

TEST(ReferenceUnwrapping, ReferenceWrapperIsRecognizedBeforeOrAfterDecay) {
  int value = 9;
  std::reference_wrapper<int> wrapped{value};

  using Unwrapped = std::unwrap_reference_t<decltype(wrapped)>;
  using DecayedUnwrapped = std::unwrap_ref_decay_t<const decltype(wrapped)&>;
  using PlainDecay = std::unwrap_ref_decay_t<const int&>;
  static_assert(std::is_same_v<Unwrapped, int&>);
  static_assert(std::is_same_v<DecayedUnwrapped, int&>);
  static_assert(std::is_same_v<PlainDecay, int>);

  DecayedUnwrapped alias = wrapped.get();
  alias = 21;
  EXPECT_EQ(value, 21);

  // unwrap_reference 只把 reference_wrapper<T> 变成 T&；unwrap_ref_decay 先 decay，
  // 因此也能识别 cv/ref 包装器。普通 const int& 会被 decay 为 int，不会意外保留别名。
}

TEST(VoidT, MapsAnyWellFormedTypeListToVoidForDetection) {
  static_assert(HasValueType<WithValueType>::value);
  static_assert(!HasValueType<WithoutValueType>::value);

  // void_t 的结果永远是 void，价值在于它的模板实参必须先成功形成类型。
  // 失败时 partial specialization 被 SFINAE 移除，回退到 false_type；现代公共接口可用 requires 表达。
}

TEST(LegacyAlignedStorage, ProvidesSizeAndAlignmentButDoesNotStartALifetime) {
  using DoubleStorage = std::aligned_storage_t<sizeof(double), alignof(double)>;
  using NumberUnionStorage = std::aligned_union_t<0, int, double>;

  static_assert(sizeof(DoubleStorage) >= sizeof(double));
  static_assert(alignof(DoubleStorage) >= alignof(double));
  static_assert(sizeof(NumberUnionStorage) >= sizeof(double));
  static_assert(alignof(NumberUnionStorage) >= alignof(double));

  // aligned_storage/aligned_union 只提供尺寸与对齐充足的类型，不会自动创建
  // 目标对象。它们在 C++23 已废弃；新代码通常用 alignas(T) std::byte[]
  // 配合 construct_at/destroy_at，让存储与对象生命期更明确。
}

TEST(ConstantEvaluation, DetectsEvaluationContextRatherThanOptimizerChoices) {
  constexpr int compile_time = evaluation_context();
  static_assert(compile_time == 1);
  EXPECT_EQ(evaluation_context(), 2);

  // is_constant_evaluated 在 manifestly constant-evaluated 语境中为 true，普通运行期
  // 调用为 false。编译器后来做常量折叠不会改变这个语义，不要把它当成优化检测器。
}

}  // namespace
