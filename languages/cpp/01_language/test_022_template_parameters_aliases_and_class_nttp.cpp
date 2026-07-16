// polyglot-covers:
// - cpp.language.type-non-type-and-template-template-parameters
// - cpp.language.default-template-arguments
// - cpp.language.alias-templates
// - cpp.language.variable-templates
// - cpp.language.auto-non-type-template-parameters
// - cpp.language.cpp20-structural-class-nttp

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <string_view>
#include <type_traits>

namespace {

template <typename Value, std::size_t Size>
class FixedBuffer {
 public:
  Value& operator[](std::size_t index) { return values_.at(index); }
  const Value& operator[](std::size_t index) const { return values_.at(index); }
  static constexpr std::size_t size = Size;

 private:
  std::array<Value, Size> values_{};
};

template <typename Value>
class SimpleBox {
 public:
  explicit SimpleBox(Value value) : value_(value) {}
  Value get() const { return value_; }

 private:
  Value value_;
};

template <typename Value, template <typename> class Wrapper = SimpleBox>
class WrappedValue {
 public:
  explicit WrappedValue(Value value) : wrapped_(value) {}
  Value get() const { return wrapped_.get(); }

 private:
  Wrapper<Value> wrapped_;
};

template <typename Value>
using RemoveCvReference = std::remove_cv_t<std::remove_reference_t<Value>>;

template <typename Value>
inline constexpr bool small_object = sizeof(Value) <= sizeof(void*);

template <auto Value>
struct AutoConstant {
  using value_type = decltype(Value);
  static constexpr auto value = Value;
};

template <std::size_t Size>
struct FixedString {
  char value[Size];

  constexpr FixedString(const char (&text)[Size]) : value{} {
    for (std::size_t index = 0; index < Size; ++index) {
      value[index] = text[index];
    }
  }
};

template <FixedString Name>
struct NamedTag {
  static constexpr auto name = Name;
};

TEST(TemplateParameters, TypeAndNonTypeParametersShapeDistinctTypes) {
  FixedBuffer<int, 3> integers;
  FixedBuffer<int, 4> larger;

  integers[0] = 7;
  larger[0] = 9;

  static_assert(FixedBuffer<int, 3>::size == 3);
  static_assert(!std::is_same_v<decltype(integers), decltype(larger)>);
  EXPECT_EQ(integers[0], 7);
  EXPECT_EQ(larger[0], 9);

  // Value 是类型参数，Size 是编译期值参数；每组实参形成不同 specialization。
  // 非类型实参必须满足常量表达式和允许类型规则，不能直接传普通运行期变量。
}

TEST(TemplateParameters, TemplateTemplateParameterAcceptsACompatibleTemplate) {
  WrappedValue<int> default_wrapper{11};
  WrappedValue<int, SimpleBox> explicit_wrapper{13};

  EXPECT_EQ(default_wrapper.get(), 11);
  EXPECT_EQ(explicit_wrapper.get(), 13);

  // template-template parameter 接收模板本身，而不是某个 SimpleBox<int> 类型。
  // 参数列表必须兼容；默认模板实参让调用者只在需要替换策略时写出包装器。
}

TEST(AliasTemplates, AliasTransformsATypeWithoutCreatingANewNominalType) {
  using Clean = RemoveCvReference<const int&>;
  static_assert(std::is_same_v<Clean, int>);

  const int value = 17;
  Clean copy = value;
  EXPECT_EQ(copy, 17);

  // alias template 只是依赖参数的类型别名，不能像 class template 那样单独特化。
  // 需要可特化的类型计算时，通常先写 traits class，再用 alias 暴露其 type。
}

TEST(VariableTemplates, ACompileTimeValueCanBeParameterizedByType) {
  static_assert(small_object<char>);
  static_assert(small_object<int>);

  struct Large {
    char bytes[64];
  };
  static_assert(!small_object<Large>);
  SUCCEED();

  // inline constexpr variable template 为每个 specialization 提供一个编译期变量，
  // 常用于 traits 的 `_v` 形式；inline 避免头文件多翻译单元定义冲突。
}

TEST(NonTypeParameters, AutoPreservesTheCompileTimeValuesExactType) {
  using Integer = AutoConstant<42>;
  using Boolean = AutoConstant<true>;

  static_assert(std::is_same_v<Integer::value_type, int>);
  static_assert(std::is_same_v<Boolean::value_type, bool>);
  static_assert(Integer::value == 42);
  static_assert(Boolean::value);

  // auto NTTP 从实参推导参数类型，因此 42、42U 和 true 产生不同 specialization。
  // 它适合值依赖算法，但调用方若需要固定 ABI 或类型约束，应显式限制 decltype(Value)。
}

TEST(NonTypeParameters, Cpp20StructuralClassCanCarryAStringAtCompileTime) {
  using Worker = NamedTag<"worker">;
  using Reader = NamedTag<"reader">;

  static_assert(!std::is_same_v<Worker, Reader>);
  EXPECT_EQ(std::string_view{Worker::name.value}, "worker");
  EXPECT_EQ(std::string_view{Reader::name.value}, "reader");

  // 字符串字面量本身不能直接作为传统 NTTP；C++20 可先转换成公开成员组成的
  // structural class。不同字符内容成为类型身份的一部分，适合编译期标签而非运行期文本。
}

}  // namespace
