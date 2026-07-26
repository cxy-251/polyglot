// polyglot-covers:
// - cpp.language.top-and-low-level-cv-qualification
// - cpp.language.mutable-members
// - cpp.language.volatile-is-not-atomic
// - cpp.language.static-const-and-reinterpret-casts
// - cpp.language.pointer-integer-roundtrip
// - cpp.language.c-style-cast-trap

#include <gtest/gtest.h>

#include <cstdint>
#include <string>
#include <type_traits>
#include <utility>

namespace {

class CachedLength {
 public:
  explicit CachedLength(std::string text) : text_(std::move(text)) {}

  std::size_t length() const {
    if (cached_length_ == 0) {
      cached_length_ = text_.size();
    }
    return cached_length_;
  }

 private:
  std::string text_;
  mutable std::size_t cached_length_{0};
};

enum class Mode : unsigned int {
  idle = 1,
  active = 2,
};

TEST(CvQualifiers, ConstCanQualifyThePointerOrThePointedObject) {
  int first = 3;
  int second = 5;

  const int* pointer_to_const = &first;
  int* const const_pointer = &first;

  pointer_to_const = &second;
  *const_pointer = 7;

  EXPECT_EQ(*pointer_to_const, 5);
  EXPECT_EQ(first, 7);

  static_assert(std::is_same_v<decltype(pointer_to_const), const int*>);
  static_assert(std::is_same_v<decltype(const_pointer), int* const>);

  // const int* 禁止通过此路径修改 int，但指针可重绑；int* const 固定指针本身，但允许
  // 修改目标。typedef/using 和模板推导中应检查 const 位于哪一层。
}

TEST(CvQualifiers, MutableSupportsLogicalConstnessForCaches) {
  const CachedLength value{"cache me"};

  EXPECT_EQ(value.length(), 8U);
  EXPECT_EQ(value.length(), 8U);

  // const 成员函数中的 this 指向 const 对象，普通成员不能修改。mutable 适合不改变
  // 对象可观察抽象值的缓存或锁；它不是逃避 const-correctness 的通用开关。
}

TEST(CvQualifiers, VolatileDoesNotProvideThreadSynchronization) {
  static_assert(!std::is_same_v<volatile int, int>);
  static_assert(std::is_volatile_v<volatile int>);

  // volatile 要求实现保留特定可观察访问，主要用于内存映射设备和信号交互。它不提供
  // 原子性、线程间 happens-before 或复合操作互斥；并发共享数据必须使用 atomic 或锁。
  SUCCEED();
}

TEST(Casts, StaticCastExpressesKnownLanguageConversions) {
  Mode mode = Mode::active;
  unsigned int raw = static_cast<unsigned int>(mode);
  Mode restored = static_cast<Mode>(raw);

  EXPECT_EQ(raw, 2U);
  EXPECT_EQ(restored, Mode::active);

  double fractional = 3.75;
  int truncated = static_cast<int>(fractional);
  EXPECT_EQ(truncated, 3);

  // static_cast 明确请求编译器已知的转换，但不自动检查数值范围。浮点转整数超出可表示
  // 范围会产生未定义行为；显式语法不等于运行期安全检查。
}

TEST(Casts, ConstCastIsSafeOnlyWhenTheUnderlyingObjectIsNotConst) {
  int mutable_value = 11;
  const int& read_only_view = mutable_value;

  int& writable_again = const_cast<int&>(read_only_view);
  writable_again = 13;
  EXPECT_EQ(mutable_value, 13);

  const int genuinely_const = 17;
  const int& const_view = genuinely_const;
  EXPECT_EQ(const_view, 17);

  // 从 genuinely_const 去掉 const 后写入仍是未定义行为。const_cast 只能恢复对象原本
  // 具有的可写性，常用于适配错误的旧接口，不能把真正的 const 对象变可变。
}

TEST(Casts, ReinterpretCastCanRoundTripThroughUintptrWhenAvailable) {
  int value = 23;
  int* pointer = &value;

  std::uintptr_t representation = reinterpret_cast<std::uintptr_t>(pointer);
  int* restored = reinterpret_cast<int*>(representation);

  EXPECT_EQ(restored, pointer);
  EXPECT_EQ(*restored, 23);

  // uintptr_t 存在时足以保存 void* 表示，指针转入再转回同类型可恢复原指针。整数值
  // 本身没有可移植地址含义；也不能借 reinterpret_cast 绕过对齐、生命周期或别名规则。
}

TEST(Casts, NamedCastsMakeTheIntentAuditable) {
  static_assert(std::is_same_v<decltype(static_cast<long>(1)), long>);

  // C 风格 `(Target)value` 会依次尝试 const_cast、static_cast、reinterpret_cast 等组合，
  // 审阅者难以看出实际采用哪条危险路径。C++ named cast 把转换类别暴露在源码和搜索中。
  SUCCEED();
}

}  // namespace
