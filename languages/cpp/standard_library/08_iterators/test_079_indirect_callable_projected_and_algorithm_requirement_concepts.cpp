// polyglot-covers:
// - cpp.stdlib.iterators.indirectly-unary-invocable-and-regular-invocable
// - cpp.stdlib.iterators.indirect-unary-and-binary-predicates
// - cpp.stdlib.iterators.indirect-equivalence-and-strict-weak-order
// - cpp.stdlib.iterators.projected-value-and-reference-types
// - cpp.stdlib.iterators.indirectly-movable-and-movable-storable
// - cpp.stdlib.iterators.indirectly-copyable-and-copyable-storable
// - cpp.stdlib.iterators.indirectly-swappable-and-comparable
// - cpp.stdlib.iterators.permutable-requirement
// - cpp.stdlib.iterators.mergeable-requirement
// - cpp.stdlib.iterators.sortable-requirement-and-projection

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <functional>
#include <iterator>
#include <list>
#include <memory>
#include <ranges>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct Record {
  std::string name;
  int score;
};

struct AddToTotal {
  int* total;

  void operator()(int value) const {
    *total += value;
  }
};

TEST(IndirectCallable, InvocableRequirementsCheckAllIteratorValueForms) {
  using Iterator = std::vector<int>::iterator;

  static_assert(std::indirectly_unary_invocable<AddToTotal, Iterator>);
  static_assert(std::indirectly_regular_unary_invocable<AddToTotal, Iterator>);

  std::vector<int> values{1, 2, 3};
  int total = 0;
  AddToTotal add{&total};
  for (auto iterator = values.begin(); iterator != values.end(); ++iterator) {
    std::invoke(add, *iterator);
  }
  EXPECT_EQ(total, 6);

  // indirect callable 不只检查 `f(*it)`，还要求 f 能处理 iter_value_t 的引用、
  // iter_reference_t 与共同引用形式。regular 版本另有“调用不修改函数或参数”的语义
  // 要求，编译器只能检查表达式结构，调用者仍须遵守语义契约。
}

TEST(IndirectPredicates, UnaryAndBinaryFormsReturnBooleanTestableResults) {
  using Iterator = std::vector<int>::iterator;
  const auto positive = [](int value) {
    return value > 0;
  };
  const auto same_parity = [](int left, int right) {
    return left % 2 == right % 2;
  };

  static_assert(std::indirect_unary_predicate<decltype(positive), Iterator>);
  static_assert(
      std::indirect_binary_predicate<decltype(same_parity), Iterator, Iterator>);

  std::vector<int> values{1, 3, 4};
  EXPECT_TRUE(std::invoke(positive, *values.begin()));
  EXPECT_TRUE(std::invoke(same_parity, values[0], values[1]));
  EXPECT_FALSE(std::invoke(same_parity, values[0], values[2]));

  // predicate 在 indirect invocable 上增加 boolean-testable 结果；binary 版本要求左右
  // value/reference 的各组合都可调用，避免代理引用只在某一种偶然组合下工作。
}

TEST(IndirectOrdering, EqualityAndOrderingConceptsCarrySemanticLaws) {
  using Iterator = std::vector<int>::iterator;

  static_assert(
      std::indirect_equivalence_relation<std::ranges::equal_to, Iterator, Iterator>);
  static_assert(
      std::indirect_strict_weak_order<std::ranges::less, Iterator, Iterator>);

  // equivalence_relation 要求自反/对称/传递，strict_weak_order 要求严格弱序；这些规律
  // 无法仅靠 requires 验证。一个能返回 bool 但顺序不传递的比较器仍会导致算法失去保证。
}

TEST(Projected, MemberPointerTurnsRecordIteratorsIntoLogicalIntIterators) {
  using Iterator = std::vector<Record>::iterator;
  using Projection = decltype(&Record::score);
  using Projected = std::projected<Iterator, Projection>;

  static_assert(std::is_same_v<std::iter_value_t<Projected>, int>);
  static_assert(std::is_same_v<std::iter_reference_t<Projected>, int&>);
  static_assert(
      std::indirect_strict_weak_order<std::ranges::less, Projected, Projected>);

  std::vector<Record> records{{"Ada", 30}, {"Grace", 20}};
  std::ranges::sort(records, std::ranges::less{}, &Record::score);
  EXPECT_EQ(records.front().name, "Grace");

  // projected<I,Proj> 是只用于约束计算的辅助类型：其读取结果等价于
  // invoke(proj,*it)。成员指针投影让算法按 score 比较，同时仍重排完整 Record。
}

TEST(IndirectMove, StorableAddsTheAbilityToMaterializeAndAssignMovedValues) {
  using Iterator = std::vector<std::unique_ptr<int>>::iterator;

  static_assert(std::indirectly_movable<Iterator, Iterator>);
  static_assert(std::indirectly_movable_storable<Iterator, Iterator>);
  static_assert(!std::indirectly_copyable<Iterator, Iterator>);

  std::vector<std::unique_ptr<int>> source;
  source.push_back(std::make_unique<int>(7));
  std::vector<std::unique_ptr<int>> destination(1);
  *destination.begin() = std::ranges::iter_move(source.begin());

  EXPECT_EQ(source.front(), nullptr);
  EXPECT_EQ(*destination.front(), 7);

  // indirectly_movable 检查 iter_move(in) 能写给 out；movable_storable 还要求值类型可从
  // rvalue read 构造并可移动赋值，供需要临时保存元素的算法使用。unique_ptr 不可复制。
}

TEST(IndirectCopy, CopyableStorableIsStrongerThanOneDirectAssignment) {
  using Input = std::vector<std::string>::iterator;
  using Output = std::vector<std::string>::iterator;

  static_assert(std::indirectly_copyable<Input, Output>);
  static_assert(std::indirectly_copyable_storable<Input, Output>);

  std::vector<std::string> source{"a", "b"};
  std::vector<std::string> destination(2);
  std::ranges::copy(source, destination.begin());
  EXPECT_EQ(destination, source);

  // copyable_storable 除了 `*out=*in`，还要求 value_type 可从各种引用构造/赋值；
  // 这支持算法先保存值再写回，而不仅是一次直接代理赋值。
}

TEST(AlgorithmRequirements, SwappableComparableAndPermutableComposeSmallerConcepts) {
  using Mutable = std::vector<int>::iterator;
  using Readonly = std::vector<int>::const_iterator;

  static_assert(std::indirectly_swappable<Mutable>);
  static_assert(std::indirectly_comparable<
                Mutable,
                Readonly,
                std::ranges::equal_to>);
  static_assert(std::permutable<Mutable>);
  static_assert(!std::permutable<Readonly>);

  // permutable 组合 forward_iterator、indirectly_movable_storable 与
  // indirectly_swappable；它表达“可在原 range 内重排”，const_iterator 因不可写而失败。
}

TEST(AlgorithmRequirements, MergeableAllowsDifferentInputsAndAnOutputIterator) {
  using Input = std::vector<int>::const_iterator;
  using Output = std::back_insert_iterator<std::vector<int>>;

  static_assert(std::mergeable<Input, Input, Output>);

  const std::vector<int> first{1, 3, 5};
  const std::vector<int> second{2, 4, 6};
  std::vector<int> result;
  std::ranges::merge(first, second, std::back_inserter(result));
  EXPECT_EQ(result, (std::vector<int>{1, 2, 3, 4, 5, 6}));

  // mergeable 要求两路可读、都能复制到输出，并能按投影后的共同关系比较；输出只需
  // weakly_incrementable，因此增长容器的 back_insert_iterator 可以满足。
}

TEST(AlgorithmRequirements, SortableDescribesElementOperationsNotTraversalCategory) {
  using VectorIterator = std::vector<Record>::iterator;
  using ListIterator = std::list<int>::iterator;

  static_assert(std::sortable<VectorIterator, std::ranges::less, decltype(&Record::score)>);
  static_assert(std::sortable<ListIterator>);
  static_assert(!std::random_access_iterator<ListIterator>);

  // sortable 只组合 permutable 与投影后的 strict weak order；它本身不要求 random
  // access。ranges::sort 的函数签名会额外要求 random_access_iterator，所以 list
  // 虽满足 sortable 元素语义，仍应调用自己的节点 sort()。
}

}  // namespace
