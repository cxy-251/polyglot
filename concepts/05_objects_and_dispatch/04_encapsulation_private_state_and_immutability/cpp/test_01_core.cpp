// 封装、私有状态与只读边界。
// 共同问题：私有成员由语法还是约定保护；只读是否深层生效；
// 调用方能否绕过封装；类型如何暴露受控更新。
//
// polyglot-family: objects_and_dispatch
// polyglot-concept: encapsulation_private_state_and_immutability
// polyglot-related: languages/cpp/language/test_016_cv_qualifiers_mutable_and_casts.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <vector>

namespace {

class Account {
 public:
  explicit Account(int balance) : balance_(balance) {}

  int balance() const { return balance_; }
  void deposit(int amount) { balance_ += amount; }

 private:
  int balance_;
};

template <typename T>
concept ExposesBalanceField = requires(T value) {
  value.balance_;
};

template <typename T>
concept ConstDepositable = requires(const T& value) {
  value.deposit(1);
};

TEST(EncapsulationConcept, PrivateMemberIsRejectedByAccessControl) {
  static_assert(!ExposesBalanceField<Account>);

  Account account{10};
  account.deposit(5);
  EXPECT_EQ(account.balance(), 15);
}

TEST(EncapsulationConcept, ConstObjectAllowsOnlyConstQualifiedInterface) {
  const Account account{10};

  EXPECT_EQ(account.balance(), 10);
  static_assert(requires(const Account& value) {
    { value.balance() } -> std::same_as<int>;
  });
}

TEST(EncapsulationConcept, ConstContainerIsShallowForPointerTargets) {
  int target = 1;
  const std::vector<int*> pointers{&target};

  *pointers[0] = 2;

  EXPECT_EQ(target, 2);
  // const 阻止修改 vector 结构和其中的指针值，不自动使指针所指对象为 const。
}

TEST(EncapsulationConcept, ConstReferenceCannotCallMutatingMember) {
  static_assert(!ConstDepositable<Account>);

  SUCCEED();
}

}  // namespace
