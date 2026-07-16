// polyglot-covers:
// - cpp.stdlib.language-support.type-info
// - cpp.stdlib.language-support.type-info-name-hash-and-order
// - cpp.stdlib.language-support.bad-typeid
// - cpp.stdlib.language-support.typeid-evaluation-rules
// - cpp.stdlib.language-support.type-index
// - cpp.stdlib.language-support.type-index-hash-key

#include <gtest/gtest.h>

#include <string>
#include <typeindex>
#include <typeinfo>
#include <unordered_map>

namespace {

struct Plain {
  int value;
};

struct PolymorphicBase {
  virtual ~PolymorphicBase() = default;
};

struct PolymorphicDerived : PolymorphicBase {};

int plain_calls = 0;
int polymorphic_calls = 0;

Plain& get_plain(Plain& value) {
  ++plain_calls;
  return value;
}

PolymorphicBase& get_polymorphic(PolymorphicBase& value) {
  ++polymorphic_calls;
  return value;
}

TEST(TypeInfo, EqualityIdentifiesTypesButNamesAreImplementationDefined) {
  const std::type_info& integer = typeid(int);
  const std::type_info& also_integer = typeid(const int);
  const std::type_info& text = typeid(std::string);

  EXPECT_EQ(integer, also_integer);
  EXPECT_NE(integer, text);
  EXPECT_FALSE(std::string{integer.name()}.empty());
  EXPECT_EQ(integer.hash_code(), also_integer.hash_code());

  // typeid(type) 忽略顶层 cv。name() 的内容、是否经过名称修饰以及 hash_code 的具体值
  // 都由实现决定，只适合当前进程内诊断或查找，不能持久化成跨编译器协议标识。
}

TEST(TypeInfo, BeforeProvidesAnImplementationOrderingWithoutSemanticMeaning) {
  const std::type_info& first = typeid(int);
  const std::type_info& second = typeid(double);

  EXPECT_NE(first.before(second), second.before(first));

  // 对不同类型，before 建立实现定义的严格弱序；它只让 type_info 可排序，不表示继承、
  // 大小或源码名字顺序。现代代码通常用 type_index 封装比较与哈希接口。
}

TEST(TypeIdEvaluation, NonpolymorphicOperandIsUnevaluated) {
  Plain value{7};
  plain_calls = 0;

  const std::type_info& observed = typeid(get_plain(value));

  EXPECT_EQ(observed, typeid(Plain));
  EXPECT_EQ(plain_calls, 0);

  // 非多态 glvalue 的 typeid 由静态类型决定，操作数不求值，所以 get_plain 没有调用。
  // 不要借 typeid(expr) 触发必要副作用；类型后来变成多态时求值行为还会改变。
}

TEST(TypeIdEvaluation, PolymorphicGlvalueIsEvaluatedForItsDynamicType) {
  PolymorphicDerived object;
  PolymorphicBase& base = object;
  polymorphic_calls = 0;

  const std::type_info& observed = typeid(get_polymorphic(base));

  EXPECT_EQ(observed, typeid(PolymorphicDerived));
  EXPECT_EQ(polymorphic_calls, 1);

  // 多态 glvalue 必须先求值得到实际对象，typeid 才能报告 dynamic type。这个分支与普通
  // unevaluated operand 直觉不同，也是 typeid 表达式需要审查副作用的原因。
}

TEST(TypeIdEvaluation, NullPolymorphicDereferenceThrowsBadTypeId) {
  PolymorphicBase* pointer = nullptr;

  EXPECT_THROW((void)typeid(*pointer), std::bad_typeid);

  // 对形如 *pointer 的多态 glvalue，空指针有专门规则抛 bad_typeid，而不是执行一次普通
  // 未定义解引用。该保护只属于 typeid 的规定语境，不能推广到其他成员访问或 dynamic_cast。
}

TEST(TypeIndex, WrapsTypeInfoForAssociativeContainers) {
  std::unordered_map<std::type_index, std::string> labels{
      {typeid(int), "integer"},
      {typeid(std::string), "text"},
  };

  EXPECT_EQ(labels.at(typeid(int)), "integer");
  EXPECT_EQ(labels.at(std::type_index{typeid(std::string)}), "text");

  // type_index 复制的是 type_info 身份的轻量包装，并提供比较与 std::hash，适合进程内
  // 类型到处理器的注册表。它仍依赖 RTTI，不能代替稳定序列化 tag 或跨动态库 ABI 设计。
}

}  // namespace
