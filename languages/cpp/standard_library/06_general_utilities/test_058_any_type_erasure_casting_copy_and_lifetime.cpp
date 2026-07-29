// polyglot-covers:
// - cpp.stdlib.utility.any-empty-state-has-value-and-type
// - cpp.stdlib.utility.any-type-erased-value-storage
// - cpp.stdlib.utility.any-cast-value-reference-and-pointer-forms
// - cpp.stdlib.utility.bad-any-cast
// - cpp.stdlib.utility.make-any-in-place-and-emplace
// - cpp.stdlib.utility.any-copy-semantics
// - cpp.stdlib.utility.any-move-reset-and-swap
// - cpp.stdlib.utility.any-copy-constructible-requirement
// - cpp.stdlib.utility.any-reference-wrapper-pattern

#include <gtest/gtest.h>

#include <any>
#include <functional>
#include <memory>
#include <string>
#include <type_traits>
#include <typeinfo>
#include <utility>
#include <vector>

namespace {

struct CopyTracked {
  static inline int copies = 0;

  explicit CopyTracked(int value) : value(value) {}
  CopyTracked(const CopyTracked& other) : value(other.value) { ++copies; }
  CopyTracked(CopyTracked&& other) noexcept : value(other.value) {
    other.value = -1;
  }

  int value;
};

TEST(Any, EmptyStateAndTypeReportTheExactStoredType) {
  std::any value;

  EXPECT_FALSE(value.has_value());
  EXPECT_EQ(value.type(), typeid(void));

  value = 42;
  EXPECT_TRUE(value.has_value());
  EXPECT_EQ(value.type(), typeid(int));
  EXPECT_NE(value.type(), typeid(long));

  // 空 any 的 type() 返回 typeid(void)，有值时返回存储类型的精确 type_info。
  // any 不会记录“可转换到哪些类型”，int 与 long 即使数值可转换也是两个不同动态类型。
}

TEST(AnyCast, ValueReferenceAndPointerFormsHaveDifferentFailureAndCopyBehavior) {
  std::any value = std::string{"payload"};

  const std::string copied = std::any_cast<std::string>(value);
  std::string& alias = std::any_cast<std::string&>(value);
  alias += "!";

  EXPECT_EQ(copied, "payload");
  EXPECT_EQ(std::any_cast<const std::string&>(value), "payload!");
  EXPECT_THROW((void)std::any_cast<int>(value), std::bad_any_cast);
  EXPECT_EQ(std::any_cast<int>(&value), nullptr);

  std::string* pointer = std::any_cast<std::string>(&value);
  ASSERT_NE(pointer, nullptr);
  EXPECT_EQ(pointer, &std::any_cast<std::string&>(value));

  // any_cast<T> 返回值并可能复制，any_cast<T&> 直接别名 contained object。
  // 引用/值版本类型不匹配会抛 bad_any_cast；指针版本则 noexcept 返回 nullptr，适合探测分支。
}

TEST(Any, CopyingCopiesTheContainedObjectWhileReferenceCastDoesNot) {
  CopyTracked::copies = 0;
  std::any original{std::in_place_type<CopyTracked>, 7};

  std::any copied = original;
  EXPECT_EQ(CopyTracked::copies, 1);

  const CopyTracked& alias = std::any_cast<const CopyTracked&>(copied);
  EXPECT_EQ(alias.value, 7);
  EXPECT_EQ(CopyTracked::copies, 1);

  const CopyTracked by_value = std::any_cast<CopyTracked>(copied);
  EXPECT_EQ(by_value.value, 7);
  EXPECT_EQ(CopyTracked::copies, 2);

  // any 是值语义容器：复制 any 必须复制其 contained object，两者随后独立。
  // 仅查看大对象时应 any_cast<const T&>，否则一个看似普通的 cast 会带来额外复制。
}

TEST(Any, MakeAnyInPlaceAndEmplaceConstructTheSelectedRuntimeType) {
  std::any values = std::make_any<std::vector<int>>(4, 3);
  EXPECT_EQ(
      std::any_cast<const std::vector<int>&>(values),
      (std::vector<int>{3, 3, 3, 3}));

  std::string& text = values.emplace<std::string>(5, 'x');
  EXPECT_EQ(&text, &std::any_cast<std::string&>(values));
  EXPECT_EQ(text, "xxxxx");
  EXPECT_EQ(values.type(), typeid(std::string));

  // make_any/in_place_type 直接构造指定动态类型，emplace 则先销毁旧对象。
  // emplace 后原 any_cast 得到的指针和引用全部失效；它返回的 T& 是新 contained object。
}

TEST(Any, MoveResetAndSwapTransferOrEndTheContainedLifetime) {
  std::any source = std::string{"source"};
  std::any target = std::move(source);

  EXPECT_EQ(std::any_cast<const std::string&>(target), "source");
  if (source.has_value()) {
    EXPECT_EQ(source.type(), typeid(std::string));
  } else {
    EXPECT_EQ(source.type(), typeid(void));
  }

  std::any number = 9;
  target.swap(number);
  EXPECT_EQ(std::any_cast<int>(target), 9);
  EXPECT_EQ(std::any_cast<const std::string&>(number), "source");

  number.reset();
  EXPECT_FALSE(number.has_value());
  EXPECT_EQ(number.type(), typeid(void));

  // move 保证目标获得源的原状态，但源 any 可以变空，也可仍包含移后 T；
  // 两种都合法。swap 可交换不同动态类型，reset 回到空状态。是否使用小对象优化是实现细节。
}

TEST(Any, StoredValuesMustBeCopyConstructibleEvenForAMoveOnlyAnyVariable) {
  static_assert(std::is_constructible_v<std::any, std::string>);
  static_assert(!std::is_constructible_v<std::any, std::unique_ptr<int>>);

  // any 自身提供复制操作，因此存入的类型必须 CopyConstructible；只会移动
  // 某一个 any 变量也不能绕过这一类型约束。移动专属所有权应用 variant 或其他明确接口建模。
}

TEST(Any, ReferenceWrapperMakesNonOwningAliasingExplicit) {
  int value = 11;
  std::any reference = std::ref(value);

  EXPECT_EQ(reference.type(), typeid(std::reference_wrapper<int>));
  std::any_cast<std::reference_wrapper<int>>(reference).get() = 17;
  EXPECT_EQ(value, 17);

  // any 的普通构造会 decay 并持有独立值，不能直接存 T&。reference_wrapper
  // 可显式表达非拥有别名，但 any_cast 目标仍是 reference_wrapper<T> 而非 T，且寿命由调用者保证。
}

}  // namespace
