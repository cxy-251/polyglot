// 对象身份、别名与复制。
// 共同问题：赋值是否复制对象；浅复制保留哪些别名；深复制如何处理对象图；
// 语言如何表达独占或共享所有权。
//
// polyglot-family: values_and_comparison
// polyglot-concept: identity_aliasing_and_copying
// polyglot-related: languages/cpp/language/test_011_object_lifetime_references_and_storage_reuse.cpp

#include <gtest/gtest.h>

#include <memory>
#include <span>
#include <type_traits>
#include <vector>

namespace {

TEST(IdentityCopyingConcept, ValueCopyAndReferenceAliasAreExplicitlyDifferent) {
  std::vector<int> original{1};
  std::vector<int> copied = original;
  std::vector<int>& alias = original;

  copied.push_back(2);
  alias.push_back(3);

  EXPECT_EQ(original, (std::vector<int>{1, 3}));
  EXPECT_EQ(copied, (std::vector<int>{1, 2}));
  EXPECT_EQ(&alias, &original);
}

TEST(IdentityCopyingConcept, NonOwningViewSharesStorageWithoutOwningLifetime) {
  std::vector<int> storage{1, 2};
  std::span<int> view = storage;

  view[0] = 9;

  EXPECT_EQ(storage[0], 9);
  EXPECT_EQ(view.data(), storage.data());

  // span 不延长 storage 生命周期；让 view 在 storage 销毁后继续存在会悬垂，这里不执行。
}

TEST(IdentityCopyingConcept, SmartPointersStateOwnershipPolicyInTheType) {
  static_assert(!std::is_copy_constructible_v<std::unique_ptr<int>>);
  static_assert(std::is_move_constructible_v<std::unique_ptr<int>>);

  auto shared = std::make_shared<int>(42);
  auto alias = shared;

  EXPECT_EQ(shared.get(), alias.get());
  EXPECT_EQ(shared.use_count(), 2);
}

TEST(IdentityCopyingConcept, DeepObjectGraphCopyRequiresAnExplicitDomainPolicy) {
  struct Node {
    int value;
    std::shared_ptr<Node> child;
  };

  Node original{1, std::make_shared<Node>(Node{2, nullptr})};
  Node shallow = original;
  shallow.child->value = 9;

  EXPECT_EQ(original.child->value, 9);

  // C++ 没有通用 deepcopy；复制 shared_ptr 保留共享关系，深复制必须由类型自己定义。
}

}  // namespace
