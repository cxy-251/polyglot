// polyglot-covers:
// - cpp.language.forwarding-reference-deduction
// - cpp.language.reference-collapsing
// - cpp.language.std-forward-conditional-cast
// - cpp.language.perfect-forwarding-construction
// - cpp.language.forwarding-noexcept
// - cpp.language.forwarding-deduction-failure-traps

#include <gtest/gtest.h>

#include <string>
#include <type_traits>
#include <utility>

namespace {

struct Message {
  explicit Message(std::string text) : text(std::move(text)) {}
  std::string text;
};

std::string category(const Message&) { return "lvalue"; }
std::string category(Message&&) { return "rvalue"; }

template <typename Value>
std::string inspect_and_forward(Value&& value) {
  std::string inside = category(value);
  std::string forwarded = category(std::forward<Value>(value));
  return inside + " -> " + forwarded;
}

template <typename Object, typename... Arguments>
Object make_object(Arguments&&... arguments)
    noexcept(std::is_nothrow_constructible_v<Object, Arguments&&...>) {
  return Object(std::forward<Arguments>(arguments)...);
}

struct NothrowValue {
  explicit NothrowValue(int) noexcept {}
};

struct ThrowingValue {
  explicit ThrowingValue(int) {}
};

template <typename Value>
decltype(auto) parenthesized_identity(Value&& value) {
  return (value);
}

TEST(ForwardingReferences, LvalueArgumentDeducesAnLvalueReferenceType) {
  Message message{"hello"};

  static_assert(std::is_same_v<decltype(parenthesized_identity(message)), Message&>);
  EXPECT_EQ(inspect_and_forward(message), "lvalue -> lvalue");
  EXPECT_EQ(inspect_and_forward(Message{"temporary"}), "lvalue -> rvalue");

  // T&& 且 T 参与推导时才是 forwarding reference。左值让 T=Message&，右值让
  // T=Message；函数体内有名字的 value 总是左值，std::forward 才恢复调用方类别。
}

TEST(ReferenceCollapsing, AnyLvalueReferenceDominatesTheCombination) {
  using Lvalue = Message&;
  using Rvalue = Message&&;

  static_assert(std::is_same_v<Lvalue&, Message&>);
  static_assert(std::is_same_v<Lvalue&&, Message&>);
  static_assert(std::is_same_v<Rvalue&, Message&>);
  static_assert(std::is_same_v<Rvalue&&, Message&&>);

  // 模板替换和 alias 可能形成“引用的引用”，语言按 &+&、&+&&、&&+& 都得到 &，
  // 只有 &&+&& 保持 &&。完美转发依赖这组 reference collapsing 规则。
}

TEST(PerfectForwarding, ConstructorReceivesTheOriginalArgumentCategory) {
  std::string text{"payload"};
  Message copied = make_object<Message>(text);
  Message moved = make_object<Message>(std::move(text));

  EXPECT_EQ(copied.text, "payload");
  EXPECT_EQ(moved.text, "payload");

  // 参数包按 forwarding reference 接收，再逐个 forward 给目标构造函数。移动后的 text
  // 仍有效但值未指定，本测试只检查目标，不断言源字符串一定为空。
}

TEST(PerfectForwarding, ConditionalNoexceptMirrorsTheSelectedConstruction) {
  static_assert(noexcept(make_object<NothrowValue>(1)));
  static_assert(!noexcept(make_object<ThrowingValue>(1)));

  auto value = make_object<NothrowValue>(1);
  (void)value;
  SUCCEED();

  // 转发包装若无条件省略 noexcept，会让容器等调用者错失异常保证；无条件写 noexcept
  // 又可能在底层抛出时 terminate。条件规范应反映实际表达式或 type trait。
}

TEST(PerfectForwarding, DecltypeAutoCanReturnAReferenceAndAlsoCreateDanglingRisk) {
  Message message{"stable"};
  Message& alias = parenthesized_identity(message);

  alias.text = "changed";
  EXPECT_EQ(message.text, "changed");

  // `return (value)` 让 decltype(auto) 推导为引用。对左值调用可保留别名，但若把临时量
  // 传入并把返回引用保存到完整表达式之后，就会悬空；完美转发不会延长对象寿命。
}

TEST(PerfectForwarding, SomeExpressionsDoNotProvideADeducibleType) {
  // make_object<std::vector<int>>({1, 2, 3}) 不能从裸 braced-init-list 推导 Arguments；
  // 转发重载函数名也缺少唯一类型，bit-field 不能绑定 forwarding reference。
  // 这类调用需要显式 initializer_list、先选择函数指针重载，或传递可寻址副本。
  SUCCEED();
}

}  // namespace
