// polyglot-covers:
// - cpp.stdlib.utility.swap-and-adl-swap-pattern
// - cpp.stdlib.utility.array-swap
// - cpp.stdlib.utility.exchange
// - cpp.stdlib.utility.move-and-forward
// - cpp.stdlib.utility.move-if-noexcept
// - cpp.stdlib.utility.as-const
// - cpp.stdlib.utility.safe-integer-comparisons
// - cpp.stdlib.utility.in-range

#include <gtest/gtest.h>

#include <array>
#include <limits>
#include <string>
#include <type_traits>
#include <utility>

namespace {

namespace adl_swap_example {

struct Record {
  std::string name;
  int* custom_swaps;

  friend void swap(Record& left, Record& right) noexcept {
    using std::swap;
    swap(left.name, right.name);
    ++*left.custom_swaps;
  }
};

}  // namespace adl_swap_example

template <typename Value>
void generic_swap(Value& left, Value& right) noexcept(std::is_nothrow_swappable_v<Value>) {
  using std::swap;
  swap(left, right);
}

struct CopyPreferred {
  static inline int copies = 0;
  static inline int moves = 0;

  explicit CopyPreferred(int value) : value(value) {}
  CopyPreferred(const CopyPreferred& other) : value(other.value) { ++copies; }
  CopyPreferred(CopyPreferred&& other) noexcept(false) : value(other.value) {
    ++moves;
  }

  int value;
};

struct MoveOnlyRisk {
  static inline int moves = 0;

  explicit MoveOnlyRisk(int value) : value(value) {}
  MoveOnlyRisk(const MoveOnlyRisk&) = delete;
  MoveOnlyRisk(MoveOnlyRisk&& other) noexcept(false) : value(other.value) {
    ++moves;
  }

  int value;
};

class ForwardedText {
 public:
  explicit ForwardedText(const std::string& text)
      : text_(text), construction_("copy source") {}

  explicit ForwardedText(std::string&& text)
      : text_(std::move(text)), construction_("move source") {}

  const std::string& text() const { return text_; }
  const std::string& construction() const { return construction_; }

 private:
  std::string text_;
  std::string construction_;
};

template <typename Argument>
ForwardedText make_forwarded_text(Argument&& argument) {
  return ForwardedText{std::forward<Argument>(argument)};
}

class QualifiedBuffer {
 public:
  std::string access() { return "mutable"; }
  std::string access() const { return "const"; }
};

TEST(Swap, GenericCodePreservesAdlCustomizationAndTheArrayOverload) {
  int custom_swaps = 0;
  adl_swap_example::Record left{"left", &custom_swaps};
  adl_swap_example::Record right{"right", &custom_swaps};

  generic_swap(left, right);
  EXPECT_EQ(left.name, "right");
  EXPECT_EQ(right.name, "left");
  EXPECT_EQ(custom_swaps, 1);

  std::array<int, 3> first{1, 2, 3};
  std::array<int, 3> second{4, 5, 6};
  std::swap(first, second);
  EXPECT_EQ(first, (std::array<int, 3>{4, 5, 6}));

  // 泛型代码先 using std::swap 再无限定调用，既保留普通 fallback，又让 ADL
  // 找到类型同命名空间的定制。直接写 std::swap(x, y) 会绕过普通的非 std ADL overload。
}

TEST(Exchange, AssignsANewValueAndReturnsThePreviousValue) {
  std::string state = "ready";
  std::string previous = std::exchange(state, "running");

  EXPECT_EQ(previous, "ready");
  EXPECT_EQ(state, "running");

  int attempts = 2;
  EXPECT_EQ(std::exchange(attempts, 0), 2);
  EXPECT_EQ(attempts, 0);

  // exchange 的语义是“先移动构造旧值，再用新值赋值”，并非 swap；新值不会
  // 被放回调用者。它适合状态迁移、取出并清零计数器等单向替换。
}

TEST(MoveIfNoexcept, CopiesWhenAThrowingMoveWouldWeakenExceptionSafety) {
  CopyPreferred::copies = 0;
  CopyPreferred::moves = 0;
  CopyPreferred source{17};

  static_assert(
      std::is_same_v<decltype(std::move_if_noexcept(source)), const CopyPreferred&>);
  CopyPreferred target{std::move_if_noexcept(source)};

  EXPECT_EQ(target.value, 17);
  EXPECT_EQ(CopyPreferred::copies, 1);
  EXPECT_EQ(CopyPreferred::moves, 0);

  // move_if_noexcept 在 move 可抛且 copy 可用时返回 const T&，让容器可用复制
  // 维持回滚能力。它只选择值类别，真正的构造仍由后续表达式执行。
}

TEST(MoveIfNoexcept, UsesAMoveWhenCopyingIsImpossible) {
  MoveOnlyRisk::moves = 0;
  MoveOnlyRisk source{23};

  static_assert(
      std::is_same_v<decltype(std::move_if_noexcept(source)), MoveOnlyRisk&&>);
  MoveOnlyRisk target{std::move_if_noexcept(source)};

  EXPECT_EQ(target.value, 23);
  EXPECT_EQ(MoveOnlyRisk::moves, 1);

  // 不可复制类型即使 move 可抛，move_if_noexcept 也只能返回 T&&。调用者
  // 不会凭空获得强异常保证；类型设计者应尽量让纯转移操作 noexcept。
}

TEST(Forward, PreservesTheCallersValueCategoryThroughAWrapper) {
  std::string reusable = "kept";
  const auto copied = make_forwarded_text(reusable);
  const auto moved = make_forwarded_text(std::string{"temporary"});

  EXPECT_EQ(copied.text(), "kept");
  EXPECT_EQ(copied.construction(), "copy source");
  EXPECT_EQ(moved.text(), "temporary");
  EXPECT_EQ(moved.construction(), "move source");

  // 命名参数 argument 在函数体内始终是 lvalue expression；std::forward<Argument>
  // 根据原始推导的 Argument 恢复调用者值类别。std::move 则会无条件把可复用实参也当成 rvalue。
}

TEST(AsConst, SelectsConstAccessWithoutCopyingOrAcceptingATemporary) {
  QualifiedBuffer buffer;

  EXPECT_EQ(buffer.access(), "mutable");
  EXPECT_EQ(std::as_const(buffer).access(), "const");
  EXPECT_EQ(&std::as_const(buffer), &buffer);
  static_assert(
      std::is_same_v<decltype(std::as_const(buffer)), const QualifiedBuffer&>);
  SUCCEED();

  // as_const 返回同一对象的 const T&，用来选 const overload 而不复制对象。
  // 它的 const rvalue overload 被删除，避免将临时对象包装成看似可长期持有的引用。
}

TEST(IntegerComparisons, SignedAndUnsignedValuesAreComparedMathematically) {
  constexpr unsigned int one = 1;
  constexpr unsigned int largest = std::numeric_limits<unsigned int>::max();

  static_assert(std::cmp_less(-1, one));
  static_assert(!std::cmp_equal(-1, largest));
  static_assert(std::cmp_greater(one, -1));
  static_assert(std::cmp_less_equal(1, one));
  static_assert(std::cmp_greater_equal(one, 1));
  static_assert(std::in_range<unsigned int>(1));
  static_assert(!std::in_range<unsigned int>(-1));
  static_assert(!std::in_range<signed char>(1'000));
  SUCCEED();

  // 普通 -1 < 1u 会先把 -1 转为很大的 unsigned，cmp_less 系列则按数学
  // 值比较并避免符号转换陷阱。这些 API 只接受标准整数类型，不是任意数字类的通用比较器。
}

}  // namespace
