// polyglot-covers:
// - cpp.stdlib.memory.addressof
// - cpp.stdlib.memory.pointer-traits
// - cpp.stdlib.memory.to-address
// - cpp.stdlib.memory.align
// - cpp.stdlib.memory.assume-aligned
// - cpp.stdlib.memory.align-val-t-and-aligned-allocation
// - cpp.stdlib.memory.nothrow-allocation
// - cpp.stdlib.memory.class-specific-allocation-function

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <new>
#include <stdexcept>
#include <type_traits>

namespace {

struct OverloadedAddress {
  OverloadedAddress* operator&() noexcept { return nullptr; }
  const OverloadedAddress* operator&() const noexcept { return nullptr; }

  int value;
};

template <typename Value>
class FancyPointer {
 public:
  using element_type = Value;
  using difference_type = std::ptrdiff_t;

  template <typename Other>
  using rebind = FancyPointer<Other>;

  FancyPointer() = default;
  explicit FancyPointer(Value* pointer) : pointer_(pointer) {}

  Value* operator->() const noexcept { return pointer_; }

  static FancyPointer pointer_to(Value& value) noexcept {
    return FancyPointer{std::addressof(value)};
  }

 private:
  Value* pointer_ = nullptr;
};

struct alignas(32) AlignedRecord {
  int value;
};

struct alignas(64) OverAlignedObject {
  int value;
};

class DeterministicNothrowObject {
 public:
  explicit DeterministicNothrowObject(int value) : value(value) {
    if (throw_next_construction) {
      throw_next_construction = false;
      throw std::runtime_error{"construction failed"};
    }
  }

  static void* operator new(
      std::size_t size,
      const std::nothrow_t&) noexcept {
    if (fail_next_allocation) {
      fail_next_allocation = false;
      return nullptr;
    }
    return ::operator new(size, std::nothrow);
  }

  static void operator delete(void* pointer) noexcept {
    ++deallocation_calls;
    ::operator delete(pointer);
  }

  static void operator delete(
      void* pointer,
      const std::nothrow_t&) noexcept {
    ++deallocation_calls;
    ::operator delete(pointer);
  }

  static inline bool fail_next_allocation = false;
  static inline bool throw_next_construction = false;
  static inline int deallocation_calls = 0;
  int value;
};

TEST(PointerUtilities, AddressofBypassesAnOverloadedAddressOperator) {
  OverloadedAddress object{17};

  EXPECT_EQ(&object, nullptr);
  OverloadedAddress* actual = std::addressof(object);
  ASSERT_NE(actual, nullptr);
  EXPECT_EQ(actual->value, 17);

  // 普通 & 可被类重载并返回与真实地址无关的值；addressof 保证取得对象实际地址。泛型
  // 容器和 allocator 不能假设 `&value` 一定是 Value*。
}

TEST(PointerUtilities, PointerTraitsDescribesAndRebindsFancyPointers) {
  int value = 23;
  using Traits = std::pointer_traits<FancyPointer<int>>;
  using ConstPointer = Traits::rebind<const int>;

  FancyPointer<int> pointer = Traits::pointer_to(value);

  static_assert(std::is_same_v<Traits::element_type, int>);
  static_assert(std::is_same_v<Traits::difference_type, std::ptrdiff_t>);
  static_assert(std::is_same_v<ConstPointer, FancyPointer<const int>>);
  EXPECT_EQ(pointer.operator->(), std::addressof(value));

  // pointer_traits 为 allocator 的 fancy pointer 提供统一 element_type、difference_type、
  // rebind 与 pointer_to 协议，不要求所有内存模型都暴露普通 T*。
}

TEST(PointerUtilities, ToAddressRecursivelyObtainsTheUnderlyingRawPointer) {
  int value = 31;
  int* raw = &value;
  FancyPointer<int> fancy{raw};
  auto owner = std::make_unique<int>(47);

  EXPECT_EQ(std::to_address(raw), raw);
  EXPECT_EQ(std::to_address(fancy), raw);
  EXPECT_EQ(std::to_address(owner), owner.get());

  // to_address 对裸指针直接返回自身，对 fancy/smart pointer 通过 pointer_traits 或
  // operator-> 递归取得地址，但不转移所有权，也不检查空指针是否可解引用。
}

TEST(Alignment, AlignAdvancesAPointerAndReducesRemainingSpace) {
  std::array<std::byte, 128> buffer{};
  void* candidate = buffer.data() + 1;
  std::size_t space = buffer.size() - 1;

  void* aligned =
      std::align(alignof(AlignedRecord), sizeof(AlignedRecord), candidate, space);
  ASSERT_NE(aligned, nullptr);
  EXPECT_EQ(aligned, candidate);
  EXPECT_EQ(reinterpret_cast<std::uintptr_t>(aligned) % alignof(AlignedRecord), 0U);

  auto* object = std::construct_at(static_cast<AlignedRecord*>(aligned), 59);
  EXPECT_EQ(object->value, 59);
  std::destroy_at(object);

  // align 成功时更新传入 pointer 到首个可用对齐地址，并扣除跳过的 padding；space 表示
  // 从新地址起的剩余字节。它不构造对象，失败时返回 nullptr 且参数保持不变。
}

TEST(Alignment, AssumeAlignedAddsACompilerContractWithoutMovingThePointer) {
  alignas(64) std::array<int, 16> values{};
  int* assumed = std::assume_aligned<64>(values.data());

  EXPECT_EQ(assumed, values.data());
  EXPECT_EQ(reinterpret_cast<std::uintptr_t>(assumed) % 64U, 0U);

  // assume_aligned 不做运行期修正或检查，只把已成立的 alignment 事实告诉优化器。传入
  // 不满足 N 对齐的指针会违反前置条件并导致未定义行为，不能用它“修复”任意地址。
}

TEST(AlignedAllocation, MatchingAlignValDeleteReleasesOverAlignedStorage) {
  constexpr auto alignment = std::align_val_t{alignof(OverAlignedObject)};
  void* storage = ::operator new(sizeof(OverAlignedObject), alignment);
  EXPECT_EQ(
      reinterpret_cast<std::uintptr_t>(storage) % alignof(OverAlignedObject),
      0U);

  auto* object = std::construct_at(
      static_cast<OverAlignedObject*>(storage),
      71);
  EXPECT_EQ(object->value, 71);

  std::destroy_at(object);
  ::operator delete(storage, alignment);

  // 显式 aligned operator new 只返回存储，随后仍要 construct_at。释放时必须传匹配的
  // align_val_t；普通 operator delete 与 aligned allocation 混用不是可移植做法。
}

TEST(NothrowAllocation, AllocationFailureReturnsNullButConstructionMayStillThrow) {
  DeterministicNothrowObject::deallocation_calls = 0;
  DeterministicNothrowObject::fail_next_allocation = true;
  auto* failed = new (std::nothrow) DeterministicNothrowObject{1};
  EXPECT_EQ(failed, nullptr);
  EXPECT_EQ(DeterministicNothrowObject::deallocation_calls, 0);

  DeterministicNothrowObject::throw_next_construction = true;
  EXPECT_THROW(
      (void)new (std::nothrow) DeterministicNothrowObject{2},
      std::runtime_error);
  EXPECT_EQ(DeterministicNothrowObject::deallocation_calls, 1);

  auto* object = new (std::nothrow) DeterministicNothrowObject{83};
  ASSERT_NE(object, nullptr);
  EXPECT_EQ(object->value, 83);
  delete object;
  EXPECT_EQ(DeterministicNothrowObject::deallocation_calls, 2);

  // nothrow 只要求分配函数在失败时返回 nullptr；对象构造函数若抛异常，new-expression
  // 仍会传播该异常，并调用匹配的 placement delete 归还刚取得的存储。
}

}  // namespace
