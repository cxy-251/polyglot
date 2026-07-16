// polyglot-covers:
// - cpp.stdlib.utility.optional-engagement-and-nullopt
// - cpp.stdlib.utility.optional-in-place-emplace-and-reset
// - cpp.stdlib.utility.optional-emplace-exception-state
// - cpp.stdlib.utility.optional-access-and-bad-optional-access
// - cpp.stdlib.utility.optional-value-or
// - cpp.stdlib.utility.optional-move-preserves-engagement
// - cpp.stdlib.utility.optional-converting-construction-and-assignment
// - cpp.stdlib.utility.optional-comparison-and-hash
// - cpp.stdlib.utility.make-optional-and-optional-swap
// - cpp.stdlib.utility.optional-reference-wrapper-pattern

#include <gtest/gtest.h>

#include <compare>
#include <functional>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace {

class TrackedValue {
 public:
  static inline int live_count = 0;

  TrackedValue(std::string name, int revision)
      : name_(std::move(name)), revision_(revision) {
    if (revision < 0) {
      throw std::invalid_argument{"negative revision"};
    }
    ++live_count;
  }

  TrackedValue(const TrackedValue& other)
      : name_(other.name_), revision_(other.revision_) {
    ++live_count;
  }

  TrackedValue(TrackedValue&& other) noexcept
      : name_(std::move(other.name_)), revision_(other.revision_) {
    ++live_count;
  }

  ~TrackedValue() { --live_count; }

  const std::string& name() const { return name_; }
  int revision() const { return revision_; }

 private:
  std::string name_;
  int revision_;
};

std::string make_fallback(int& calls) {
  ++calls;
  return "fallback";
}

TEST(Optional, DefaultAndNulloptConstructionCreateADisengagedState) {
  std::optional<int> first;
  std::optional<int> second = std::nullopt;
  std::optional<int> engaged = 0;

  EXPECT_FALSE(first.has_value());
  EXPECT_FALSE(static_cast<bool>(second));
  EXPECT_TRUE(engaged.has_value());
  EXPECT_EQ(*engaged, 0);

  // optional 的状态是“是否包含 T 对象”，不是把 0、空字符串或 nullptr 猜成缺失。
  // nullopt 是显式的无值标记；已参与的 optional<int>{0} 仍然包含一个有效 int。
}

TEST(Optional, InPlaceEmplaceAndResetManageTheContainedLifetime) {
  TrackedValue::live_count = 0;
  std::optional<TrackedValue> value{
      std::in_place,
      "draft",
      1,
  };

  ASSERT_TRUE(value);
  EXPECT_EQ(value->name(), "draft");
  EXPECT_EQ(TrackedValue::live_count, 1);

  TrackedValue& replacement = value.emplace("published", 2);
  EXPECT_EQ(&replacement, &*value);
  EXPECT_EQ(value->revision(), 2);
  EXPECT_EQ(TrackedValue::live_count, 1);

  value.reset();
  EXPECT_FALSE(value);
  EXPECT_EQ(TrackedValue::live_count, 0);

  // in_place 直接用参数构造 T，emplace 先销毁旧 T 再原地构造新 T，返回
  // 新对象引用。reset 只结束 contained object 生命期，optional 容器自身仍可再次 emplace。
}

TEST(Optional, FailedEmplaceLeavesTheOptionalDisengaged) {
  TrackedValue::live_count = 0;
  std::optional<TrackedValue> value{
      std::in_place,
      "valid",
      1,
  };

  EXPECT_THROW(value.emplace("invalid", -1), std::invalid_argument);
  EXPECT_FALSE(value.has_value());
  EXPECT_EQ(TrackedValue::live_count, 0);

  // emplace 必须先销毁已有值；新构造随后抛异常时，旧值不会回滚，optional
  // 留在 disengaged 状态。若业务需要“成功才替换”，应先在外部构造临时值再赋值或 swap。
}

TEST(Optional, ValueChecksStateWhileDereferenceRequiresAPrecondition) {
  std::optional<std::string> present{"text"};
  std::optional<std::string> missing;

  EXPECT_EQ(present.value(), "text");
  EXPECT_EQ(present->size(), 4U);
  EXPECT_THROW((void)missing.value(), std::bad_optional_access);
  static_assert(
      std::is_same_v<decltype(*std::move(present)), std::string&&>);

  // value() 在空状态抛 bad_optional_access，operator* 和 operator-> 则要求调用者
  // 已确认有值；解引用 disengaged optional 不会安全返回默认值，而是未定义行为。
}

TEST(Optional, ValueOrEagerlyBuildsItsArgumentAndReturnsAnOwnedValue) {
  int fallback_calls = 0;
  const std::optional<std::string> present{"configured"};
  const std::optional<std::string> missing;

  const std::string chosen = present.value_or(make_fallback(fallback_calls));
  EXPECT_EQ(chosen, "configured");
  EXPECT_EQ(fallback_calls, 1);

  const std::string defaulted = missing.value_or(make_fallback(fallback_calls));
  EXPECT_EQ(defaulted, "fallback");
  EXPECT_EQ(fallback_calls, 2);

  // value_or 是普通函数，fallback 实参在进入函数前就会求值，即使 optional
  // 已有值也一样。它返回 T 而非引用；昂贵或有副作用的惰性 fallback 应先显式 if 判断。
}

TEST(Optional, MovingTheWrapperDoesNotDisengageTheSource) {
  std::optional<std::string> source{"payload"};
  std::optional<std::string> target{std::move(source)};

  ASSERT_TRUE(target);
  EXPECT_EQ(*target, "payload");
  EXPECT_TRUE(source.has_value());

  // optional 的 move constructor 移动的是 contained T，不是 engagement bit。源 optional
  // 仍然有值，但其 string 处于合法但未指定的移后状态，因此不断言它一定为空。
}

TEST(Optional, ConvertingConstructionAndAssignmentFollowContainedConversions) {
  std::optional<int> integer{12};
  std::optional<long> widened = integer;

  ASSERT_TRUE(widened);
  EXPECT_EQ(*widened, 12L);

  integer = std::nullopt;
  widened = integer;
  EXPECT_FALSE(widened);

  // optional<U> 到 optional<T> 传递两层信息：源空则目标空，源有值才用 U
  // 构造或赋给 T。这不是调用 value_or(T{})，不会把缺失悄悄转成默认 T。
}

TEST(Optional, OrderingAndHashingIncludeTheEngagementState) {
  const std::optional<int> missing;
  const std::optional<int> low{2};
  const std::optional<int> high{7};

  EXPECT_LT(missing, low);
  EXPECT_LT(low, high);
  EXPECT_EQ(low, 2);
  EXPECT_EQ(std::hash<std::optional<int>>{}(low), std::hash<int>{}(2));
  static_assert(
      std::is_same_v<decltype(low <=> high), std::strong_ordering>);

  // 排序时 disengaged optional 小于任何 engaged optional，两边都有值时再比 T。
  // 有值状态的 hash 与 contained T 的 hash 一致；空状态的具体 hash 值未指定，不要持久化。
}

TEST(Optional, MakeOptionalAndSwapMoveTheWholeEngagementState) {
  auto value = std::make_optional<std::string>(4, 'x');
  std::optional<std::string> missing;

  value.swap(missing);
  EXPECT_FALSE(value);
  ASSERT_TRUE(missing);
  EXPECT_EQ(*missing, "xxxx");

  // make_optional<T>(args...) 像 in_place 一样直接构造 T，并返回已参与的 optional。
  // swap 交换的不只是 T 的值，还包括 engagement；一空一非空时会移动构造目标并销毁源值。
}

TEST(Optional, ReferenceWrapperRepresentsAnOptionalNonOwningReference) {
  int value = 5;
  std::optional<std::reference_wrapper<int>> reference = std::ref(value);

  reference->get() = 13;
  EXPECT_EQ(value, 13);
  reference = std::nullopt;
  EXPECT_FALSE(reference);

  // optional<T&> 不是标准允许的 specialization。若要表示可缺失的非拥有引用，
  // 可用 optional<reference_wrapper<T>>，但调用者仍必须保证被引用对象比 optional 长寿。
}

}  // namespace
