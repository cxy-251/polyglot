// polyglot-covers:
// - cpp.stdlib.iterators.iterator-traits-value-reference-difference-and-pointer
// - cpp.stdlib.iterators.iter-value-reference-rvalue-reference-and-difference-aliases
// - cpp.stdlib.iterators.iterator-concept-hierarchy
// - cpp.stdlib.iterators.contiguous-iterator-to-address-relationship
// - cpp.stdlib.iterators.input-output-forward-bidirectional-random-contiguous-semantics
// - cpp.stdlib.iterators.indirectly-readable-and-writable
// - cpp.stdlib.iterators.ranges-iter-move-fallback-and-adl-customization
// - cpp.stdlib.iterators.ranges-iter-swap-fallback-and-adl-customization

#include <gtest/gtest.h>

#include <array>
#include <concepts>
#include <cstddef>
#include <deque>
#include <forward_list>
#include <iterator>
#include <list>
#include <memory>
#include <ranges>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct CustomMoveIterator {
  using value_type = std::string;
  using difference_type = std::ptrdiff_t;
  using iterator_concept = std::input_iterator_tag;
  using iterator_category = std::input_iterator_tag;

  std::string* current = nullptr;

  std::string& operator*() const noexcept {
    return *current;
  }

  CustomMoveIterator& operator++() noexcept {
    ++current;
    return *this;
  }

  CustomMoveIterator operator++(int) noexcept {
    auto old = *this;
    ++*this;
    return old;
  }

  friend bool operator==(
      const CustomMoveIterator&,
      const CustomMoveIterator&) = default;

  friend std::string iter_move(const CustomMoveIterator& iterator) {
    return "custom:" + *iterator.current;
  }
};

struct CustomSwapIterator {
  using value_type = int;
  using difference_type = std::ptrdiff_t;
  using iterator_concept = std::forward_iterator_tag;
  using iterator_category = std::forward_iterator_tag;

  static inline int calls = 0;
  int* current = nullptr;

  int& operator*() const noexcept {
    return *current;
  }

  CustomSwapIterator& operator++() noexcept {
    ++current;
    return *this;
  }

  CustomSwapIterator operator++(int) noexcept {
    auto old = *this;
    ++*this;
    return old;
  }

  friend bool operator==(
      const CustomSwapIterator&,
      const CustomSwapIterator&) = default;

  friend void iter_swap(CustomSwapIterator left, CustomSwapIterator right) noexcept {
    ++calls;
    std::swap(*left, *right);
  }
};

TEST(IteratorTraits, ClassicTraitsDescribeTheAssociatedTypes) {
  using Iterator = std::vector<long>::iterator;
  using Traits = std::iterator_traits<Iterator>;

  static_assert(std::is_same_v<typename Traits::value_type, long>);
  static_assert(std::is_same_v<typename Traits::reference, long&>);
  static_assert(std::is_same_v<typename Traits::difference_type, std::ptrdiff_t>);
  static_assert(std::is_same_v<typename Traits::iterator_category,
                               std::random_access_iterator_tag>);

  static_assert(std::is_same_v<std::iterator_traits<int*>::value_type, int>);
  static_assert(std::is_same_v<std::iterator_traits<int*>::pointer, int*>);

  // iterator_traits 统一访问用户迭代器与原生指针的关联类型。difference_type 必须能表示
  // 同一序列中两个迭代器的距离；不要用无符号 size_type 替代它。
}

TEST(IteratorTraits, Cpp20AliasesObserveDereferenceAndIterMoveSeparately) {
  using Iterator = std::vector<std::unique_ptr<int>>::iterator;

  static_assert(std::is_same_v<std::iter_value_t<Iterator>, std::unique_ptr<int>>);
  static_assert(
      std::is_same_v<std::iter_reference_t<Iterator>, std::unique_ptr<int>&>);
  static_assert(
      std::is_same_v<std::iter_rvalue_reference_t<Iterator>, std::unique_ptr<int>&&>);
  static_assert(std::is_same_v<std::iter_difference_t<Iterator>, std::ptrdiff_t>);

  // iter_value_t 是逻辑值类型，iter_reference_t 来自 *it，iter_rvalue_reference_t
  // 来自 ranges::iter_move(it)。代理迭代器中这三者不必是 T、T&、T&& 的简单组合。
}

TEST(IteratorConcepts, StandardIteratorsFormARefinementHierarchy) {
  using Forward = std::forward_list<int>::iterator;
  using Bidirectional = std::list<int>::iterator;
  using Random = std::deque<int>::iterator;
  using Contiguous = std::vector<int>::iterator;

  static_assert(std::input_iterator<Forward>);
  static_assert(std::forward_iterator<Forward>);
  static_assert(!std::bidirectional_iterator<Forward>);

  static_assert(std::bidirectional_iterator<Bidirectional>);
  static_assert(!std::random_access_iterator<Bidirectional>);

  static_assert(std::random_access_iterator<Random>);
  static_assert(!std::contiguous_iterator<Random>);

  static_assert(std::contiguous_iterator<Contiguous>);
  static_assert(std::random_access_iterator<Contiguous>);

  // 每一层增加语义和复杂度保证：forward 可多遍读取，bidirectional 可 --，random
  // access 可常数时间跳转，contiguous 还保证地址与偏移和真实连续存储一致。
}

TEST(IteratorConcepts, ContiguousIteratorMatchesToAddressAndDereference) {
  std::vector<int> values{2, 3, 5};
  auto iterator = values.begin() + 1;

  static_assert(std::contiguous_iterator<decltype(iterator)>);
  EXPECT_EQ(std::to_address(iterator), &*iterator);
  EXPECT_EQ(std::to_address(iterator), values.data() + 1);

  // contiguous_iterator 不只是“支持 +”；标准保证 to_address(i)==addressof(*i)，
  // 并且 i+n 对应地址+n。deque iterator 虽可随机访问，却不满足这一物理布局保证。
}

TEST(IndirectConcepts, ReadabilityAndWritabilityDescribeOperationsThroughAnIterator) {
  using Mutable = std::vector<int>::iterator;
  using Readonly = std::vector<int>::const_iterator;
  using Output = std::back_insert_iterator<std::vector<int>>;

  static_assert(std::indirectly_readable<Mutable>);
  static_assert(std::indirectly_readable<Readonly>);
  static_assert(std::indirectly_writable<Mutable, int>);
  static_assert(!std::indirectly_writable<Readonly, int>);
  static_assert(std::indirectly_writable<Output, int>);
  static_assert(!std::indirectly_readable<Output>);

  // output iterator 可写但没有可读值，const_iterator 可读但不可写。算法用间接概念
  // 表达 `*it` 上的真实需求，通常比只检查 iterator_category 更准确。
}

TEST(IterMove, DefaultBehaviorProducesAnRvalueReferenceToTheElement) {
  std::string value = "payload";
  std::string* iterator = &value;

  static_assert(
      std::is_same_v<decltype(std::ranges::iter_move(iterator)), std::string&&>);
  std::string moved = std::ranges::iter_move(iterator);

  EXPECT_EQ(moved, "payload");

  // 没有 ADL 定制时，iter_move 对普通 lvalue 解引用结果做 std::move；它本身不搬移，
  // 直到返回的 xvalue 被构造或赋值消费。源 string 只保证处于有效但未指定状态。
}

TEST(IterMove, AdlCustomizationCanDefineTheLogicalRvalueRead) {
  std::array<std::string, 1> values{"payload"};
  CustomMoveIterator iterator{values.data()};

  static_assert(std::input_iterator<CustomMoveIterator>);
  static_assert(
      std::is_same_v<std::iter_rvalue_reference_t<CustomMoveIterator>, std::string>);

  auto result = std::ranges::iter_move(iterator);

  EXPECT_EQ(result, "custom:payload");
  EXPECT_EQ(values[0], "payload");

  // ranges::iter_move 先寻找 ADL iter_move。代理或变换迭代器可借此定义“移动读取”
  // 的逻辑值，而不必暴露真实 T&&；返回 prvalue 也完全有效。
}

TEST(IterSwap, FallbackSwapsReferencesAndAdlCanOverrideTheOperation) {
  std::array<int, 2> plain{1, 2};
  std::ranges::iter_swap(plain.begin(), plain.begin() + 1);
  EXPECT_EQ(plain, (std::array<int, 2>{2, 1}));

  std::array<int, 2> customized{3, 4};
  CustomSwapIterator::calls = 0;
  CustomSwapIterator first{customized.data()};
  CustomSwapIterator second{customized.data() + 1};

  static_assert(std::indirectly_swappable<CustomSwapIterator>);
  std::ranges::iter_swap(first, second);

  EXPECT_EQ(customized, (std::array<int, 2>{4, 3}));
  EXPECT_EQ(CustomSwapIterator::calls, 1);

  // iter_swap 优先使用 ADL 定制，否则尝试 ranges::swap(*a,*b)，再回退到 iter_move
  // 组成的交换。算法应调用该定制点，才能正确处理代理引用和特殊交换语义。
}

}  // namespace
