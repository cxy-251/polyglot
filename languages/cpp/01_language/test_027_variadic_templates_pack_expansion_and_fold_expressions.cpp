// polyglot-covers:
// - cpp.language.variadic-template-parameter-packs
// - cpp.language.sizeof-pack-and-pack-expansion
// - cpp.language.unary-and-binary-fold-expressions
// - cpp.language.fold-association-and-empty-pack-identities
// - cpp.language.comma-fold-evaluation-order
// - cpp.language.pack-expansion-in-base-and-using-declarations
// - cpp.language.cxx20-lambda-pack-init-capture

#include <gtest/gtest.h>

#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <typename... Values>
auto sum(Values... values) {
  return (0 + ... + values);
}

template <typename... Conditions>
bool all(Conditions... conditions) {
  return (true && ... && conditions);
}

template <typename... Values>
auto subtract_left(Values... values) {
  static_assert(sizeof...(Values) > 0);
  return (... - values);
}

template <typename... Values>
auto subtract_right(Values... values) {
  static_assert(sizeof...(Values) > 0);
  return (values - ...);
}

template <typename... Actions>
void invoke_in_order(Actions&&... actions) {
  (std::forward<Actions>(actions)(), ...);
}

template <typename... Callables>
struct Overload : Callables... {
  using Callables::operator()...;
};

template <typename... Callables>
Overload(Callables...) -> Overload<Callables...>;

template <typename... Values>
auto capture_pack(Values... values) {
  return [...copies = std::move(values)] { return (0 + ... + copies); };
}

TEST(ParameterPacks, SizeofPackCountsArgumentsWithoutExpandingThem) {
  auto count_types = []<typename... Types>(Types&&...) {
    return sizeof...(Types);
  };

  EXPECT_EQ(count_types(1, 2.0, "three"), 3U);
  EXPECT_EQ(count_types(), 0U);

  // parameter pack 表示零个或多个参数，sizeof... 直接得到元素数量。pack 本身不能作为
  // 普通单值使用；必须在允许的 pattern 中用 ... 展开，或传给另一个 pack。
}

TEST(FoldExpressions, BinaryFoldProvidesAnIdentityForAnEmptyPack) {
  EXPECT_EQ(sum(), 0);
  EXPECT_EQ(sum(1, 2, 3, 4), 10);
  EXPECT_TRUE(all());
  EXPECT_FALSE(all(true, true, false));

  // `(init op ... op pack)` 是 binary fold，init 为 + 提供 0、为 && 提供 true。
  // 没有 init 的 unary fold 只对 &&、|| 和逗号定义空包 identity，其他运算会非法。
}

TEST(FoldExpressions, LeftAndRightFoldsHaveDifferentAssociation) {
  EXPECT_EQ(subtract_left(10, 3, 2), 5);
  EXPECT_EQ(subtract_right(10, 3, 2), 9);

  // unary left fold 展开为 (10 - 3) - 2，unary right fold 展开为 10 - (3 - 2)。
  // 对非结合运算符，括号方向是 API 语义的一部分，不能随意互换折叠形式。
}

TEST(FoldExpressions, CommaFoldRunsActionsFromLeftToRight) {
  std::vector<int> events;

  invoke_in_order(
      [&] { events.push_back(1); },
      [&] { events.push_back(2); },
      [&] { events.push_back(3); });

  EXPECT_EQ(events, (std::vector<int>{1, 2, 3}));

  // 内建逗号运算符保证左侧 sequenced before 右侧，因此 comma fold 适合有序执行包中
  // 操作。用 + fold 聚合带副作用表达式则不能从折叠括号推导求值顺序。
}

TEST(ParameterPacks, ExpandingBaseClassesBuildsAnOverloadSet) {
  auto visitor = Overload{
      [](int value) { return "int " + std::to_string(value); },
      [](const std::string& value) { return "string " + value; },
  };

  EXPECT_EQ(visitor(7), "int 7");
  EXPECT_EQ(visitor(std::string{"text"}), "string text");

  // `Callables...` 展开为多个基类，`using Callables::operator()...` 再把每个调用运算符
  // 引入一个重载集合。这是 std::visit 常见 visitor 适配器背后的语言机制。
}

TEST(ParameterPacks, Cpp20InitCaptureCanExpandOneClosureMemberPerValue) {
  auto total = capture_pack(1, 2, 3);
  EXPECT_EQ(total(), 6);

  static_assert(std::is_copy_constructible_v<decltype(total)>);

  // `[...copies = expression]` 为包中每个元素创建一个 init-capture 成员。若某个成员
  // move-only，闭包的复制能力也会按成员特殊成员规则自动受限。
}

}  // namespace
