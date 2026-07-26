// polyglot-covers:
// - cpp.language.operator-overloading
// - cpp.language.hidden-friend-and-adl
// - cpp.language.prefix-and-postfix-increment
// - cpp.language.subscript-call-and-arrow-operators
// - cpp.language.user-defined-conversions
// - cpp.language.defaulted-equality-and-three-way-comparison
// - cpp.language.partial-ordering

#include <gtest/gtest.h>

#include <compare>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

class Counter {
 public:
  explicit Counter(int value = 0) : value_(value) {}

  Counter& operator+=(const Counter& other) {
    value_ += other.value_;
    return *this;
  }

  friend Counter operator+(Counter left, const Counter& right) {
    left += right;
    return left;
  }

  Counter& operator++() {
    ++value_;
    return *this;
  }

  Counter operator++(int) {
    Counter old{*this};
    ++(*this);
    return old;
  }

  friend bool operator==(const Counter&, const Counter&) = default;

  [[nodiscard]] int value() const { return value_; }

 private:
  int value_;
};

class CheckedSequence {
 public:
  explicit CheckedSequence(std::vector<int> values) : values_(std::move(values)) {}

  int& operator[](std::size_t index) { return values_.at(index); }
  const int& operator[](std::size_t index) const { return values_.at(index); }

  int operator()(std::size_t index, int scale) const {
    return values_.at(index) * scale;
  }

 private:
  std::vector<int> values_;
};

struct Payload {
  int value;
};

class PayloadHandle {
 public:
  explicit PayloadHandle(Payload* pointer) : pointer_(pointer) {}
  Payload* operator->() const { return pointer_; }
  Payload& operator*() const { return *pointer_; }

 private:
  Payload* pointer_;
};

class ExplicitNumber {
 public:
  explicit ExplicitNumber(int value) : value_(value) {}
  explicit operator int() const { return value_; }
  explicit operator bool() const { return value_ != 0; }

 private:
  int value_;
};

struct Version {
  int major;
  int minor;
  int patch;

  auto operator<=>(const Version&) const = default;
};

struct Measurement {
  double value;

  auto operator<=>(const Measurement&) const = default;
};

TEST(OperatorOverloading, CompoundAssignmentCanPowerTheBinaryOperator) {
  Counter left{7};
  Counter right{5};

  Counter sum = left + right;
  EXPECT_EQ(sum.value(), 12);
  EXPECT_EQ(left.value(), 7);

  left += right;
  EXPECT_EQ(left.value(), 12);

  // 把 operator+ 写成按值取得左操作数并复用 operator+=，能自然支持左侧临时量和移动。
  // hidden friend 只通过 ADL 找到，既保持对称转换机会，也不污染外围普通名字查找。
}

TEST(OperatorOverloading, PrefixAndPostfixIncrementReturnDifferentValues) {
  Counter value{3};

  Counter& prefix_result = ++value;
  EXPECT_EQ(&prefix_result, &value);
  EXPECT_EQ(value.value(), 4);

  Counter old = value++;
  EXPECT_EQ(old.value(), 4);
  EXPECT_EQ(value.value(), 5);

  // 后缀形式用未命名的 int 哑参数与前缀形式区分，并返回修改前的副本；前缀通常
  // 返回 *this 的引用。自定义迭代器若不需要旧值，应优先使用前缀以避免潜在复制。
}

TEST(OperatorOverloading, SubscriptAndCallOperatorsCanModelDifferentProtocols) {
  CheckedSequence sequence{{2, 3, 5}};
  const CheckedSequence& read_only = sequence;

  sequence[1] = 7;
  EXPECT_EQ(read_only[1], 7);
  EXPECT_EQ(sequence(2, 10), 50);
  EXPECT_THROW((void)sequence[9], std::out_of_range);

  // const 与非 const 下标重载分别返回只读和可写引用；operator() 让对象表现为函数。
  // 重载不会改变 [] 或 () 的优先级、结合性和操作数数量，只定义类型参与时的行为。
}

TEST(OperatorOverloading, ArrowRecursesUntilItProducesARawPointer) {
  Payload payload{41};
  PayloadHandle handle{&payload};

  EXPECT_EQ(handle->value, 41);
  handle->value += 1;
  EXPECT_EQ((*handle).value, 42);

  // 对类类型执行 a->member 时，编译器反复调用 operator->，直到得到原始指针再做
  // 成员访问。这允许多层代理，但每层都必须保持被指对象的寿命和 const 语义。
}

TEST(Conversions, ExplicitOperatorsRequireAnIntentionalConversion) {
  ExplicitNumber number{7};

  static_assert(!std::is_convertible_v<ExplicitNumber, int>);
  EXPECT_EQ(static_cast<int>(number), 7);

  if (number) {
    SUCCEED();
  } else {
    FAIL() << "explicit operator bool participates in a condition";
  }

  // explicit 转换运算符不会参与普通隐式转换，但 explicit operator bool 仍可用于条件
  // 的 contextual conversion。这样既支持 if，又避免对象意外进入整数算术。
}

TEST(Comparisons, DefaultedSpaceshipComparesMembersLexicographically) {
  Version stable{2, 3, 1};
  Version older_patch{2, 3, 0};
  Version older_minor{2, 2, 99};

  static_assert(std::is_same_v<decltype(stable <=> older_patch), std::strong_ordering>);
  EXPECT_GT(stable, older_patch);
  EXPECT_GT(stable, older_minor);
  EXPECT_EQ(stable, (Version{2, 3, 1}));

  // 默认 operator<=> 按基类和非 static 成员声明顺序做词典序比较，并可合成 <、<=、
  // >、>=；默认比较同时支持生成相符的 operator==，减少六个运算符彼此不一致的风险。
}

TEST(Comparisons, FloatingPointMemberProducesAPartialOrdering) {
  Measurement normal{1.0};
  Measurement nan{std::numeric_limits<double>::quiet_NaN()};

  static_assert(std::is_same_v<decltype(normal <=> nan), std::partial_ordering>);
  EXPECT_EQ(normal <=> nan, std::partial_ordering::unordered);
  EXPECT_FALSE(normal < nan);
  EXPECT_FALSE(normal > nan);
  EXPECT_FALSE(normal == nan);

  // double 含 NaN，不能形成所有值都可比较的 strong_ordering。默认 spaceship 会把成员
  // 的最弱比较类别传播到整个类型；调用者必须处理 unordered，而不是只检查小于或大于。
}

}  // namespace
