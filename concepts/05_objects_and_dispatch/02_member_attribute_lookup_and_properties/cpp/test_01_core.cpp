// 成员、属性查找与 property。
// 共同问题：实例与类型成员的查找顺序是什么；访问器如何获得接收者；
// 数据描述符能否覆盖实例字典；缺失属性如何定制。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: member_attribute_lookup_and_properties
// polyglot-related: languages/cpp/language/test_034_class_members_ref_qualifiers_and_member_pointers.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <stdexcept>
#include <string>

namespace {

class Product {
 public:
  explicit Product(int price) {
    set_price(price);
  }

  int price() const { return price_; }
  int doubled() const { return price_ * 2; }

  void set_price(int value) {
    if (value <= 0) {
      throw std::invalid_argument{"must be positive"};
    }
    price_ = value;
  }

 private:
  int price_ = 0;
};

template <typename T>
concept HasUnknownMember = requires(T value) {
  value.unknown;
};

TEST(MemberLookupConcept, AccessorsAreOrdinaryMemberFunctions) {
  Product product{5};

  EXPECT_EQ(product.price(), 5);
  EXPECT_EQ(product.doubled(), 10);
  EXPECT_THROW(product.set_price(0), std::invalid_argument);
}

TEST(MemberLookupConcept, MemberPointerNeedsAnExplicitReceiver) {
  Product product{5};
  auto getter = &Product::price;

  EXPECT_EQ((product.*getter)(), 5);
}

TEST(MemberLookupConcept, MissingMemberIsACompileTimeError) {
  static_assert(!HasUnknownMember<Product>);

  // C++ 不提供 Python __getattr__ 或 JavaScript Proxy 的通用运行期缺失成员钩子。
}

TEST(MemberLookupConcept, PrivateStorageCannotBeShadowedByDynamicProperties) {
  Product product{5};

  EXPECT_EQ(product.price(), 5);
  // 对象没有实例字典；成员集合与访问控制由静态类型定义。
}

}  // namespace

