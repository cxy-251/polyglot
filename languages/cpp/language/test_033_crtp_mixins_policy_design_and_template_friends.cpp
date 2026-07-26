// polyglot-covers:
// - cpp.language.crtp-static-polymorphism
// - cpp.language.crtp-hidden-friend
// - cpp.language.mixin-template
// - cpp.language.policy-based-design
// - cpp.language.template-friend
// - cpp.language.cross-specialization-friendship

#include <gtest/gtest.h>

#include <string>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <typename Derived>
class Printable {
 public:
  std::string print() const {
    return static_cast<const Derived&>(*this).print_impl();
  }

 protected:
  Printable() = default;
};

class Invoice : public Printable<Invoice> {
 public:
  explicit Invoice(int number) : number_(number) {}

  std::string print_impl() const { return "invoice #" + std::to_string(number_); }

 private:
  int number_;
};

template <typename Derived>
struct EqualityComparable {
  friend bool operator==(const Derived& left, const Derived& right) {
    return left.equality_key() == right.equality_key();
  }
};

class Coordinate : public EqualityComparable<Coordinate> {
 public:
  Coordinate(int x, int y) : x_(x), y_(y) {}

  auto equality_key() const { return std::tie(x_, y_); }

 private:
  int x_;
  int y_;
};

struct VectorStorage {
  void store(std::string message) { messages.push_back(std::move(message)); }
  std::vector<std::string> messages;
};

struct PrefixFormat {
  std::string format(const std::string& message) const { return "[log] " + message; }
};

struct PlainFormat {
  std::string format(const std::string& message) const { return message; }
};

template <typename StoragePolicy, typename FormatPolicy>
class Logger : private StoragePolicy, private FormatPolicy {
 public:
  void write(const std::string& message) {
    StoragePolicy::store(FormatPolicy::format(message));
  }

  const auto& messages() const { return StoragePolicy::messages; }
};

template <typename Value>
class SecretBox;

template <typename Value>
struct Inspector {
  static Value read(const SecretBox<Value>& box) { return box.value_; }
};

template <typename Value>
class SecretBox {
 public:
  explicit SecretBox(Value value) : value_(std::move(value)) {}

  template <typename>
  friend struct Inspector;

  template <typename>
  friend class SecretBox;

  template <typename Other>
  Other copy_as() const {
    return static_cast<Other>(SecretBox<Other>{static_cast<Other>(value_)}.value_);
  }

 private:
  Value value_;
};

TEST(Crtp, BaseCallsDerivedBehaviorWithoutVirtualDispatch) {
  const Invoice invoice{27};
  EXPECT_EQ(invoice.print(), "invoice #27");
  static_assert(!std::is_polymorphic_v<Invoice>);

  // CRTP 把派生类型作为模板实参交给基类，static_cast 在编译期绑定 print_impl。它没有
  // 虚表和运行期替换能力；若需要异构集合或运行期插件，应使用 virtual 或 type erasure。
}

TEST(Mixins, HiddenFriendOperatorIsFoundByAdl) {
  const Coordinate first{2, 3};
  const Coordinate same{2, 3};
  const Coordinate other{3, 2};

  EXPECT_TRUE(first == same);
  EXPECT_FALSE(first == other);

  // 每个 Derived specialization 注入一个只接受该类型的 hidden friend。普通名称查找
  // 看不到它，但表达式的 ADL 会从 Coordinate 的关联类找到，避免污染外围重载集合。
}

TEST(PolicyDesign, OrthogonalPoliciesComposeBehaviorAtCompileTime) {
  Logger<VectorStorage, PrefixFormat> prefixed;
  Logger<VectorStorage, PlainFormat> plain;

  prefixed.write("ready");
  plain.write("ready");

  EXPECT_EQ(prefixed.messages(), std::vector<std::string>{"[log] ready"});
  EXPECT_EQ(plain.messages(), std::vector<std::string>{"ready"});

  // policy 通过模板参数替换正交行为，编译器可内联调用；代价是每个组合都是不同类型，
  // 组合过多会增加编译时间和代码体积。private inheritance 也隐藏了策略实现细节。
}

TEST(TemplateFriends, FriendTemplateCanAccessMatchingPrivateState) {
  const SecretBox<int> box{42};
  EXPECT_EQ(Inspector<int>::read(box), 42);

  // template friend 声明让 Inspector 的所有 specialization 成为 friend，并非只授权
  // Inspector<Value>。若权限必须更窄，应预先声明模板后精确写 friend struct Inspector<Value>。
}

TEST(TemplateFriends, DifferentClassSpecializationsAreOtherwiseDistinctClasses) {
  const SecretBox<int> box{7};
  EXPECT_DOUBLE_EQ(box.copy_as<double>(), 7.0);

  // SecretBox<int> 与 SecretBox<double> 是两个独立类，默认不能互访 private。这里显式把
  // 所有 SecretBox specialization 声明为 friend，copy_as 才能读取另一 specialization。
}

}  // namespace
