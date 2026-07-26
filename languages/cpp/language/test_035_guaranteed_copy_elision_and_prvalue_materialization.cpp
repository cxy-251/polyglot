// polyglot-covers:
// - cpp.language.guaranteed-copy-elision
// - cpp.language.unnamed-return-value-optimization
// - cpp.language.named-return-value-optimization
// - cpp.language.prvalue-result-object
// - cpp.language.temporary-materialization-conversion
// - cpp.language.implicit-move-on-return

#include <gtest/gtest.h>

#include <type_traits>
#include <utility>

namespace {

struct Trace {
  static inline int direct_constructions = 0;
  static inline int copies = 0;
  static inline int moves = 0;
  static inline int destructions = 0;

  explicit Trace(int value) : value(value) { ++direct_constructions; }

  Trace(const Trace& other) : value(other.value) { ++copies; }

  Trace(Trace&& other) noexcept : value(other.value) {
    ++moves;
    other.value = -1;
  }

  ~Trace() { ++destructions; }

  static void reset() {
    direct_constructions = 0;
    copies = 0;
    moves = 0;
    destructions = 0;
  }

  int value;
};

Trace make_prvalue(int value) { return Trace{value}; }

Trace make_named_value(int value) {
  Trace result{value};
  return result;
}

struct Immovable {
  explicit Immovable(int value) : value(value) {}
  Immovable(const Immovable&) = delete;
  Immovable(Immovable&&) = delete;

  int value;
};

Immovable make_immovable(int value) { return Immovable{value}; }

int consume_immovable(Immovable value) { return value.value; }

TEST(CopyElision, SameTypePrvalueConstructsDirectlyInTheDestination) {
  Trace::reset();
  {
    Trace result = make_prvalue(42);

    EXPECT_EQ(result.value, 42);
    EXPECT_EQ(Trace::direct_constructions, 1);
    EXPECT_EQ(Trace::copies, 0);
    EXPECT_EQ(Trace::moves, 0);
    EXPECT_EQ(Trace::destructions, 0);
  }
  EXPECT_EQ(Trace::destructions, 1);

  // C++17 起，同类型 prvalue 直接在最终 result 的存储中构造，不是“先造临时量再允许
  // 编译器优化掉 move”。因此副作用计数也必须表现为只有一个对象。
}

TEST(CopyElision, GuaranteedCasesDoNotRequireCopyOrMoveConstructors) {
  const Immovable result = make_immovable(17);
  EXPECT_EQ(result.value, 17);
  EXPECT_EQ(consume_immovable(Immovable{9}), 9);

  static_assert(!std::is_copy_constructible_v<Immovable>);
  static_assert(!std::is_move_constructible_v<Immovable>);

  // 返回同类型 prvalue、再用同类型 prvalue 初始化按值参数，都直接构造 result object，
  // 所以删除 copy/move 仍合法。析构函数仍必须在返回点可访问且未删除。
}

TEST(CopyElision, NamedReturnValueOptimizationIsPermittedButNotGuaranteed) {
  Trace::reset();
  Trace result = make_named_value(23);

  EXPECT_EQ(result.value, 23);
  EXPECT_EQ(Trace::copies, 0);
  EXPECT_LE(Trace::moves, 1);

  // NRVO 针对具名局部变量，是许可优化而非保证语义；未做 NRVO 时 return 会把合格的
  // 局部对象当作右值尝试 move。测试不能强行要求计数为零，也不应写 std::move(result)
  // 阻止 NRVO。
}

TEST(Prvalues, BindingAReferenceMaterializesATemporaryAndExtendsItsLifetime) {
  Trace::reset();
  {
    const Trace& reference = Trace{31};
    EXPECT_EQ(reference.value, 31);
    EXPECT_EQ(Trace::direct_constructions, 1);
    EXPECT_EQ(Trace::destructions, 0);
  }
  EXPECT_EQ(Trace::destructions, 1);

  // prvalue 在需要 glvalue 的引用绑定处发生 temporary materialization，产生可绑定对象；
  // 直接绑定的局部 const reference 把该对象寿命延长到引用作用域结束。
}

TEST(CopyElision, DifferentTargetTypesStillNeedAConversion) {
  struct Wrapper {
    explicit Wrapper(Trace source) : stored(std::move(source)) {}
    Trace stored;
  };

  Trace::reset();
  const Wrapper wrapper{make_prvalue(8)};

  EXPECT_EQ(wrapper.stored.value, 8);
  EXPECT_EQ(Trace::direct_constructions, 1);
  EXPECT_EQ(Trace::moves, 1);

  // make_prvalue 的 Trace 可直接成为 Wrapper 参数对象，但参数再初始化成员 stored 是
  // 不同的目标对象，需执行 move。保证复制消除只适用于规则指定的同类型 result object。
}

}  // namespace
