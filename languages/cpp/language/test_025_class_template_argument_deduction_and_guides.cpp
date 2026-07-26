// polyglot-covers:
// - cpp.language.class-template-argument-deduction
// - cpp.language.implicit-and-user-defined-deduction-guides
// - cpp.language.aggregate-ctad
// - cpp.language.deduction-guide-decay-policy
// - cpp.language.member-templates-and-injected-class-name
// - cpp.language.ctad-does-not-convert-an-object

#include <gtest/gtest.h>

#include <cstddef>
#include <string>
#include <type_traits>
#include <utility>

namespace {

template <typename First, typename Second>
class PairValue {
 public:
  PairValue(First first, Second second)
      : first_(std::move(first)), second_(std::move(second)) {}

  const First& first() const { return first_; }
  const Second& second() const { return second_; }

 private:
  First first_;
  Second second_;
};

template <typename Value>
class DecayBox {
 public:
  explicit DecayBox(Value value) : value_(std::move(value)) {}

  template <typename Target>
  Target as() const {
    return static_cast<Target>(value_);
  }

  DecayBox copy() const { return *this; }

 private:
  Value value_;
};

template <typename Value>
DecayBox(Value&&) -> DecayBox<std::decay_t<Value>>;

template <typename Value, std::size_t Size>
struct StaticSequence {
  Value values[Size];
};

template <typename First, typename... Rest>
StaticSequence(First, Rest...)
    -> StaticSequence<std::common_type_t<First, Rest...>, 1 + sizeof...(Rest)>;

template <std::size_t Size>
class LiteralText {
 public:
  explicit LiteralText(const char (&text)[Size]) : value_{} {
    for (std::size_t index = 0; index < Size; ++index) {
      value_[index] = text[index];
    }
  }

  std::string str() const { return std::string{value_, Size - 1}; }
  static constexpr std::size_t extent = Size;

 private:
  char value_[Size];
};

TEST(Ctad, ConstructorParametersCreateImplicitDeductionGuides) {
  PairValue pair{7, std::string{"seven"}};

  static_assert(std::is_same_v<decltype(pair), PairValue<int, std::string>>);
  EXPECT_EQ(pair.first(), 7);
  EXPECT_EQ(pair.second(), "seven");

  // 类模板构造函数产生 fictional deduction candidates，从实参推导 First/Second 后才
  // 实例化 PairValue<int,string> 并调用真实构造函数。CTAD 只决定类型，不转换对象。
}

TEST(Ctad, UserGuideCanChooseToStoreADecayedValue) {
  int number = 11;
  DecayBox box{number};

  static_assert(std::is_same_v<decltype(box), DecayBox<int>>);
  EXPECT_EQ(box.as<long>(), 11L);

  number = 13;
  EXPECT_EQ(box.as<int>(), 11);

  // guide 的 Value&& 是 forwarding reference，但结果显式使用 decay_t<Value>，所以左值
  // 实参仍存副本而不是 DecayBox<int&>。guide 本身没有函数体，也不负责保存值。
}

TEST(Ctad, UserGuideCanSupplyAnAggregateSpecialization) {
  StaticSequence sequence{1, 2L, 3};

  static_assert(std::is_same_v<decltype(sequence), StaticSequence<long, 3>>);
  EXPECT_EQ(sequence.values[0], 1L);
  EXPECT_EQ(sequence.values[2], 3L);

  // C++20 aggregate 可参与 CTAD；这里显式 guide 计算 common_type 和元素数量，随后
  // 仍由聚合初始化填充数组。推导成功不代表窄化或成员初始化规则被跳过。
}

TEST(Ctad, ArrayReferenceParameterDeducesAStringLiteralExtent) {
  LiteralText text{"hello"};

  static_assert(decltype(text)::extent == 6);
  EXPECT_EQ(text.str(), "hello");

  // 构造参数 const char(&)[Size] 保留字符串数组 extent，隐式 guide 因而推导 Size=6。
  // 若参数改为 const char*，CTAD 无法恢复已经退化丢失的长度。
}

TEST(ClassTemplates, MemberTemplateHasItsOwnIndependentParameterList) {
  DecayBox integer{7};

  EXPECT_DOUBLE_EQ(integer.as<double>(), 7.0);
  static_assert(std::is_same_v<decltype(integer.copy()), DecayBox<int>>);

  // as<Target> 的 Target 独立于类的 Value；类作用域中的裸 DecayBox 是 injected-class-name，
  // 在此 specialization 内等价于 DecayBox<Value>，所以 copy() 不必重复模板实参。
}

}  // namespace
