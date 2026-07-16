// polyglot-covers:
// - cpp.language.nonstatic-and-static-data-members
// - cpp.language.inline-static-data-member
// - cpp.language.this-pointer-and-cv-qualified-member-functions
// - cpp.language.ref-qualified-member-functions
// - cpp.language.pointer-to-data-member
// - cpp.language.pointer-to-member-function
// - cpp.language.nested-class-and-friend-access

#include <gtest/gtest.h>

#include <functional>
#include <string>
#include <type_traits>
#include <utility>

namespace {

class TextBuffer {
 public:
  explicit TextBuffer(std::string text) : text_(std::move(text)) {}

  std::string& text() & { return text_; }
  const std::string& text() const& { return text_; }
  std::string text() && { return std::move(text_); }

 private:
  std::string text_;
};

struct Device {
  int level = 0;

  int adjust(int amount) {
    level += amount;
    return level;
  }

  int projected(int amount) const { return level + amount; }
};

class SerialNumber {
 public:
  SerialNumber() : value_(next_value_++) {}

  int value() const { return value_; }

  static void reset(int first) { next_value_ = first; }

 private:
  inline static int next_value_ = 1;
  int value_;
};

class VaultInspector;

class Vault {
 public:
  explicit Vault(int secret) : secret_(secret) {}

  class NestedReader {
   public:
    static int read(const Vault& vault) { return vault.secret_; }
  };

 private:
  friend class VaultInspector;
  int secret_;
};

class VaultInspector {
 public:
  static int read(const Vault& vault) { return vault.secret_; }
};

TEST(MemberFunctions, CvAndRefQualifiersDescribeTheRequiredObjectExpression) {
  TextBuffer mutable_buffer{"mutable"};
  const TextBuffer constant_buffer{"constant"};

  static_assert(std::is_same_v<decltype(mutable_buffer.text()), std::string&>);
  static_assert(std::is_same_v<decltype(constant_buffer.text()), const std::string&>);
  static_assert(
      std::is_same_v<decltype(TextBuffer{"temporary"}.text()), std::string>);

  mutable_buffer.text() += " changed";
  EXPECT_EQ(mutable_buffer.text(), "mutable changed");
  EXPECT_EQ(std::move(mutable_buffer).text(), "mutable changed");

  // const 限定控制 this 指向对象的可修改性；尾部 &/&& 再按对象表达式的值类别选择重载。
  // 临时对象返回值而非内部引用，可避免完整表达式结束后留下悬空引用。
}

TEST(MemberPointers, DataMemberPointerNeedsAnObjectToProduceAnLvalue) {
  int Device::* level_member = &Device::level;
  Device device{3};
  Device* pointer = &device;

  device.*level_member = 7;
  EXPECT_EQ(pointer->*level_member, 7);
  EXPECT_EQ(std::invoke(level_member, device), 7);

  static_assert(std::is_same_v<decltype(Device::level), int>);
  static_assert(std::is_same_v<decltype((device.level)), int&>);

  // 成员指针不是成员在某个对象中的地址；它描述如何在兼容对象内定位成员，必须结合
  // `.*`、`->*` 或 invoke 使用。括号也让 decltype 从实体规则切换到表达式类别规则。
}

TEST(MemberPointers, MemberFunctionPointerIncludesCvQualification) {
  int (Device::*mutating)(int) = &Device::adjust;
  int (Device::*observing)(int) const = &Device::projected;
  Device device{10};

  EXPECT_EQ((device.*mutating)(2), 12);
  EXPECT_EQ(std::invoke(observing, std::as_const(device), 5), 17);

  // const 成员函数限定属于成员函数指针类型，不能赋给缺少 const 的指针类型。invoke
  // 统一处理对象、对象指针和 reference_wrapper，泛型代码无需手写 `.*` 分支。
}

TEST(StaticMembers, InlineStaticMemberIsSharedByAllObjects) {
  SerialNumber::reset(100);
  const SerialNumber first;
  const SerialNumber second;

  EXPECT_EQ(first.value(), 100);
  EXPECT_EQ(second.value(), 101);

  // static data member 不存在于每个对象子对象中；inline 允许在类定义内给出头文件安全的
  // 定义。static member function 没有 this，只能直接访问静态成员或显式接收对象。
}

TEST(AccessControl, NestedClassAndDeclaredFriendCanAccessPrivateMembers) {
  const Vault vault{73};

  EXPECT_EQ(Vault::NestedReader::read(vault), 73);
  EXPECT_EQ(VaultInspector::read(vault), 73);

  // nested class 是独立类型，没有隐式外围 Vault 对象，但拥有访问外围 private 的权限。
  // friend 授权也不建立继承、成员关系或传递性，只影响声明中指定实体的访问检查。
}

}  // namespace
