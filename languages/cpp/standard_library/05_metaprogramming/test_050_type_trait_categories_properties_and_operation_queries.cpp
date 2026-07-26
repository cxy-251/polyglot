// polyglot-covers:
// - cpp.stdlib.meta.integral-constant-interface
// - cpp.stdlib.meta.primary-type-categories
// - cpp.stdlib.meta.composite-type-categories
// - cpp.stdlib.meta.bounded-and-unbounded-array-traits
// - cpp.stdlib.meta.type-properties
// - cpp.stdlib.meta.signed-unsigned-and-unique-representation-properties
// - cpp.stdlib.meta.supported-operation-traits
// - cpp.stdlib.meta.rank-extent-and-alignment-queries
// - cpp.stdlib.meta.incomplete-type-preconditions

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <cstring>
#include <type_traits>
#include <utility>

namespace {

union NumberStorage {
  int integer;
  double real;
};

enum class State : unsigned char { idle, running };

struct MemberOwner {
  int data;
  int read() const { return data; }
};

struct PlainRecord {
  int id;
  double score;
};

struct DefaultMemberValue {
  int value = 0;
};

struct EmptyTag {};

struct PolymorphicBase {
  virtual ~PolymorphicBase() = default;
  virtual int value() const = 0;
};

struct Concrete final : PolymorphicBase {
  int value() const override { return 7; }
};

class ExplicitNumber {
 public:
  explicit ExplicitNumber(int value) : value_(value) {}
  int value() const { return value_; }

 private:
  int value_;
};

struct NoDefault {
  NoDefault() = delete;
  explicit NoDefault(int value) : value(value) {}
  int value;
};

struct ThrowingMove {
  ThrowingMove() = default;
  ThrowingMove(ThrowingMove&&) noexcept(false) {}
};

struct NoThrowMove {
  NoThrowMove() = default;
  NoThrowMove(NoThrowMove&&) noexcept = default;
};

struct DeletedDestructor {
  ~DeletedDestructor() = delete;
};

namespace throwing_swap_example {

struct Value {
  int number;

  friend void swap(Value& left, Value& right) noexcept(false) {
    std::swap(left.number, right.number);
  }
};

}  // namespace throwing_swap_example

struct alignas(64) CacheLineValue {
  int value;
};

struct Incomplete;

template <typename Value>
concept CompleteType = requires { sizeof(Value); };

TEST(IntegralConstant, ExposesAValueAsBothATypeAndAConstantExpression) {
  using Four = std::integral_constant<int, 4>;

  static_assert(Four::value == 4);
  static_assert(std::is_same_v<Four::value_type, int>);
  static_assert(std::is_same_v<Four::type, Four>);
  static_assert(Four{}() == 4);
  static_assert(static_cast<int>(Four{}) == 4);
  static_assert(std::bool_constant<(Four::value % 2 == 0)>::value);
  SUCCEED();

  // integral_constant 把值放入类型，同时提供 value、转换运算符和 operator()。
  // 因此 trait 结果既能参与模板继承与重载，也能像普通 constexpr 值一样使用。
}

TEST(TypeCategories, PrimaryTraitsDistinguishLanguageTypesNotLibraryWrappers) {
  using Function = int(double);
  using FunctionPointer = int (*)(double);

  static_assert(std::is_void_v<void>);
  static_assert(std::is_null_pointer_v<std::nullptr_t>);
  static_assert(std::is_integral_v<const int>);
  static_assert(std::is_floating_point_v<volatile double>);
  static_assert(std::is_array_v<int[3]>);
  static_assert(!std::is_array_v<std::array<int, 3>>);
  static_assert(std::is_pointer_v<FunctionPointer>);
  static_assert(std::is_function_v<Function>);
  static_assert(!std::is_function_v<FunctionPointer>);
  static_assert(std::is_lvalue_reference_v<int&>);
  static_assert(std::is_rvalue_reference_v<int&&>);
  static_assert(std::is_enum_v<State>);
  static_assert(std::is_union_v<NumberStorage>);
  static_assert(std::is_class_v<MemberOwner>);
  SUCCEED();

  // primary category 描述语言类型系统，不按“看起来像容器”分类。std::array
  // 是 class type 而非 array type；函数类型与指向函数的指针也是两个不同类别。
}

TEST(TypeCategories, MemberPointersAndCompositeCategoriesHavePreciseBoundaries) {
  using DataPointer = decltype(&MemberOwner::data);
  using MethodPointer = decltype(&MemberOwner::read);

  static_assert(std::is_member_object_pointer_v<DataPointer>);
  static_assert(std::is_member_function_pointer_v<MethodPointer>);
  static_assert(std::is_member_pointer_v<DataPointer>);
  static_assert(!std::is_pointer_v<DataPointer>);

  static_assert(std::is_arithmetic_v<double>);
  static_assert(std::is_fundamental_v<void>);
  static_assert(std::is_scalar_v<int*>);
  static_assert(std::is_object_v<int[2]>);
  static_assert(!std::is_object_v<void>);
  static_assert(!std::is_object_v<int&>);
  static_assert(std::is_compound_v<MemberOwner>);
  static_assert(std::is_reference_v<const int&>);
  SUCCEED();

  // pointer-to-member 需要配合对象才能访问，不是普通地址，所以 is_pointer 为
  // false。is_object 也不是“所有可声明的类型”：void、引用和函数都不是对象类型。
}

TEST(ArrayTraits, BoundednessRankAndExtentPreserveArrayShape) {
  using Matrix = int[2][3];
  using OpenRows = int[][3];

  static_assert(std::is_bounded_array_v<Matrix>);
  static_assert(!std::is_unbounded_array_v<Matrix>);
  static_assert(std::is_unbounded_array_v<OpenRows>);
  static_assert(std::rank_v<Matrix> == 2);
  static_assert(std::extent_v<Matrix, 0> == 2);
  static_assert(std::extent_v<Matrix, 1> == 3);
  static_assert(std::extent_v<OpenRows, 0> == 0);
  static_assert(std::extent_v<OpenRows, 1> == 3);
  static_assert(std::rank_v<int*> == 0);
  SUCCEED();

  // 未知第一维的数组仍是 unbounded array，extent 用 0 表示未知边界；
  // 这不等于空数组。已退化成 T* 后维度信息已丢失，rank 只能得到 0。
}

TEST(TypeProperties, TrivialCopyabilityIsNotTheSameAsTrivialConstruction) {
  static_assert(std::is_trivial_v<PlainRecord>);
  static_assert(std::is_trivially_copyable_v<PlainRecord>);
  static_assert(std::is_standard_layout_v<PlainRecord>);
  static_assert(std::is_aggregate_v<PlainRecord>);

  static_assert(!std::is_trivial_v<DefaultMemberValue>);
  static_assert(std::is_trivially_copyable_v<DefaultMemberValue>);
  static_assert(std::is_standard_layout_v<DefaultMemberValue>);

  const DefaultMemberValue source{37};
  DefaultMemberValue copied{};
  std::memcpy(&copied, &source, sizeof(source));
  EXPECT_EQ(copied.value, 37);

  // default member initializer 使默认构造不再 trivial，却不必然破坏
  // trivially-copyable。只有后一类型才允许用 memcpy 复制对象值；不要用类名猜测。
}

TEST(TypeProperties, SignednessAndUniqueRepresentationsAreFormalProperties) {
  static_assert(std::is_signed_v<int>);
  static_assert(std::is_unsigned_v<unsigned int>);
  static_assert(std::is_unsigned_v<bool>);
  static_assert(std::has_unique_object_representations_v<unsigned char>);
  SUCCEED();

  // is_unsigned 按标准算术语义分类，所以 bool 也是 unsigned；这不代表它
  // 适合计数。has_unique_object_representations 为 true 表示相同值不会有两种对象表示，
  // 但不保证字节序、跨平台布局，也不保证 memcmp 的顺序等于数值顺序。
}

TEST(TypeProperties, EmptyPolymorphicAbstractAndFinalDescribeSeparateFacts) {
  static_assert(std::is_empty_v<EmptyTag>);
  static_assert(sizeof(EmptyTag) >= 1);
  static_assert(std::is_polymorphic_v<PolymorphicBase>);
  static_assert(std::is_abstract_v<PolymorphicBase>);
  static_assert(!std::is_abstract_v<Concrete>);
  static_assert(std::is_final_v<Concrete>);
  static_assert(std::has_virtual_destructor_v<PolymorphicBase>);
  SUCCEED();

  // empty 只表示没有非静态数据等状态，独立对象仍要有可区分地址。polymorphic、
  // abstract 和 final 是正交属性：有虚函数不等于不能实例化，final 也不等于不可复制。
}

TEST(OperationTraits, ConstructionConversionAssignmentAndDestructionAreDistinct) {
  static_assert(std::is_constructible_v<ExplicitNumber, int>);
  static_assert(!std::is_convertible_v<int, ExplicitNumber>);
  static_assert(!std::is_default_constructible_v<NoDefault>);
  static_assert(std::is_constructible_v<NoDefault, int>);
  static_assert(std::is_assignable_v<int&, int>);
  static_assert(!std::is_assignable_v<int, int>);
  static_assert(std::is_destructible_v<int>);
  static_assert(!std::is_destructible_v<DeletedDestructor>);

  const ExplicitNumber number{11};
  EXPECT_EQ(number.value(), 11);

  // constructible 包含 explicit constructor，convertible 问的却是隐式转换。assignable
  // 检查的是左侧表达式，因此通常应传 T&；只传 T 会把可赋值类型误判为 false。
}

TEST(OperationTraits, NothrowAndTrivialVariantsExpressOptimizationContracts) {
  static_assert(std::is_move_constructible_v<ThrowingMove>);
  static_assert(!std::is_nothrow_move_constructible_v<ThrowingMove>);
  static_assert(std::is_nothrow_move_constructible_v<NoThrowMove>);
  static_assert(std::is_trivially_copy_constructible_v<PlainRecord>);
  static_assert(std::is_trivially_copy_assignable_v<PlainRecord>);
  static_assert(std::is_trivially_destructible_v<PlainRecord>);
  static_assert(std::is_nothrow_destructible_v<PlainRecord>);
  static_assert(std::is_swappable_v<throwing_swap_example::Value>);
  static_assert(!std::is_nothrow_swappable_v<throwing_swap_example::Value>);
  SUCCEED();

  // “操作存在”与“操作不抛异常”是两层信息。容器扩容等通用代码常依据
  // nothrow move 决定能否安全移动；不应因为 move constructor 可编译就假定强异常保证。
}

TEST(PropertyQueries, AlignmentIsACompileTimePropertyOfTheType) {
  static_assert(std::alignment_of_v<CacheLineValue> == alignof(CacheLineValue));
  static_assert(std::alignment_of_v<CacheLineValue> == 64);
  static_assert(CompleteType<CacheLineValue>);
  static_assert(!CompleteType<Incomplete>);
  SUCCEED();

  // 部分 type property trait 对未完整类型有前置条件：若补全类型可能改变结果，
  // 提前实例化 trait 可导致未定义行为而非可检测的 false。这里先用 sizeof 约束完整性。
}

}  // namespace
