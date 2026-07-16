// polyglot-covers:
// - cpp.stdlib.memory.allocator-traits-rebind
// - cpp.stdlib.memory.allocator-equality
// - cpp.stdlib.memory.select-on-container-copy-construction
// - cpp.stdlib.memory.allocator-propagation-traits
// - cpp.stdlib.memory.uses-allocator
// - cpp.stdlib.memory.make-obj-using-allocator
// - cpp.stdlib.memory.scoped-allocator-adaptor
// - cpp.stdlib.memory.nested-container-allocator-propagation

#include <gtest/gtest.h>

#include <cstddef>
#include <memory>
#include <scoped_allocator>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct AllocationState {
  std::size_t allocated_objects = 0;
  std::size_t deallocated_objects = 0;
  int copy_selections = 0;
};

template <typename Value>
class CountingAllocator {
 public:
  using value_type = Value;
  using propagate_on_container_move_assignment = std::true_type;
  using is_always_equal = std::false_type;

  CountingAllocator() noexcept = default;
  explicit CountingAllocator(AllocationState& state) noexcept : state_(&state) {}

  template <typename Other>
  CountingAllocator(const CountingAllocator<Other>& other) noexcept
      : state_(other.state()) {}

  Value* allocate(std::size_t count) {
    if (state_ != nullptr) {
      state_->allocated_objects += count;
    }
    return std::allocator<Value>{}.allocate(count);
  }

  void deallocate(Value* pointer, std::size_t count) noexcept {
    if (state_ != nullptr) {
      state_->deallocated_objects += count;
    }
    std::allocator<Value>{}.deallocate(pointer, count);
  }

  CountingAllocator select_on_container_copy_construction() const {
    if (state_ != nullptr) {
      ++state_->copy_selections;
    }
    return *this;
  }

  AllocationState* state() const noexcept { return state_; }

 private:
  AllocationState* state_ = nullptr;
};

template <typename Left, typename Right>
bool operator==(
    const CountingAllocator<Left>& left,
    const CountingAllocator<Right>& right) noexcept {
  return left.state() == right.state();
}

template <typename Left, typename Right>
bool operator!=(
    const CountingAllocator<Left>& left,
    const CountingAllocator<Right>& right) noexcept {
  return !(left == right);
}

class AllocatorAwareValue {
 public:
  using allocator_type = CountingAllocator<std::byte>;

  AllocatorAwareValue(
      std::allocator_arg_t,
      const allocator_type& allocator,
      int value)
      : allocator_state_(allocator.state()), value_(value) {}

  AllocationState* allocator_state() const noexcept { return allocator_state_; }
  int value() const noexcept { return value_; }

 private:
  AllocationState* allocator_state_;
  int value_;
};

TEST(AllocatorTraits, RebindPreservesAllocatorStateForAnotherValueType) {
  AllocationState state;
  using IntegerAllocator = CountingAllocator<int>;
  using DoubleAllocator =
      std::allocator_traits<IntegerAllocator>::rebind_alloc<double>;

  IntegerAllocator integers{state};
  DoubleAllocator doubles{integers};

  double* storage = doubles.allocate(2);
  EXPECT_EQ(doubles.state(), &state);
  EXPECT_EQ(state.allocated_objects, 2U);
  doubles.deallocate(storage, 2);
  EXPECT_EQ(state.deallocated_objects, 2U);

  // allocator_traits::rebind_alloc 为容器内部节点等不同类型取得兼容 allocator。转换构造
  // 应保留资源身份；若 rebind 悄悄换资源，分配与释放可能落到不同 allocator 实例。
}

TEST(AllocatorTraits, ContainerCopyUsesTheAllocatorSelectionCustomization) {
  AllocationState state;
  using Allocator = CountingAllocator<int>;

  std::vector<int, Allocator> original{Allocator{state}};
  original.push_back(3);
  original.push_back(5);

  const auto copied = original;
  ASSERT_EQ(copied.size(), 2U);
  EXPECT_EQ(copied[0], 3);
  EXPECT_EQ(copied[1], 5);
  EXPECT_EQ(copied.get_allocator().state(), &state);
  EXPECT_EQ(state.copy_selections, 1);

  // copy construction 通过 select_on_container_copy_construction 选择目标 allocator，默认
  // 通常复制原 allocator，但有状态资源可显式选择新的 arena。元素复制与 allocator 选择
  // 是两套独立语义。
}

TEST(AllocatorTraits, MoveAssignmentCanPropagateTheSourceAllocator) {
  AllocationState source_state;
  AllocationState target_state;
  using Allocator = CountingAllocator<int>;

  std::vector<int, Allocator> source{{7, 11}, Allocator{source_state}};
  std::vector<int, Allocator> target{{1}, Allocator{target_state}};

  target = std::move(source);

  ASSERT_EQ(target.size(), 2U);
  EXPECT_EQ(target[0], 7);
  EXPECT_EQ(target[1], 11);
  EXPECT_EQ(target.get_allocator().state(), &source_state);

  // propagate_on_container_move_assignment=true 允许目标接管源 allocator 和存储。若为 false
  // 且 allocator 不相等，容器通常必须逐元素移动，复杂度和迭代器有效性都会不同。
}

TEST(UsesAllocator, StandardHelperSelectsTheAllocatorArgConstructorForm) {
  AllocationState state;
  CountingAllocator<std::byte> allocator{state};

  static_assert(std::uses_allocator_v<AllocatorAwareValue, decltype(allocator)>);
  const auto value =
      std::make_obj_using_allocator<AllocatorAwareValue>(allocator, 42);

  EXPECT_EQ(value.value(), 42);
  EXPECT_EQ(value.allocator_state(), &state);

  // uses_allocator 协议识别 allocator_type，并在 allocator_arg 前置形式或 allocator 后置
  // 形式中选择可构造者。make_obj_using_allocator 把这套分派封装成普通对象构造。
}

TEST(ScopedAllocator, PropagatesAnInnerAllocatorIntoNestedContainers) {
  AllocationState state;
  using InnerAllocator = CountingAllocator<int>;
  using InnerVector = std::vector<int, InnerAllocator>;
  using OuterAllocator = CountingAllocator<InnerVector>;
  using ScopedAllocator =
      std::scoped_allocator_adaptor<OuterAllocator, InnerAllocator>;

  ScopedAllocator allocator{OuterAllocator{state}, InnerAllocator{state}};
  std::vector<InnerVector, ScopedAllocator> matrix{allocator};
  matrix.emplace_back();
  matrix.back().push_back(13);

  ASSERT_EQ(matrix.size(), 1U);
  ASSERT_EQ(matrix.front().size(), 1U);
  EXPECT_EQ(matrix.front().front(), 13);
  EXPECT_EQ(matrix.front().get_allocator().state(), &state);

  // 普通外层 allocator 只管理 InnerVector 对象本身；scoped_allocator_adaptor 在构造内层
  // uses-allocator 对象时继续传入 inner_allocator，避免嵌套容器悄悄退回默认资源。
}

TEST(AllocatorEquality, ResourceIdentityDeterminesStorageInterchangeability) {
  AllocationState first_state;
  AllocationState second_state;

  const CountingAllocator<int> first{first_state};
  const CountingAllocator<long> same_resource{first_state};
  const CountingAllocator<int> other{second_state};

  EXPECT_EQ(first, same_resource);
  EXPECT_NE(first, other);
  static_assert(
      !std::allocator_traits<CountingAllocator<int>>::is_always_equal::value);

  // allocator 相等表示一方能释放另一方取得的存储，不是“配置字段恰好相同”。有状态
  // allocator 通常按底层资源身份比较，并把 is_always_equal 设为 false。
}

}  // namespace
