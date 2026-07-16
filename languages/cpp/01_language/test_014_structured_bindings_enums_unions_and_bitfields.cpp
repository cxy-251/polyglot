// polyglot-covers:
// - cpp.language.structured-binding-array-and-tuple-protocol
// - cpp.language.scoped-and-unscoped-enumerations
// - cpp.language.enum-underlying-type
// - cpp.language.union-active-member-and-common-initial-sequence
// - cpp.language.bitfields

#include <gtest/gtest.h>

#include <array>
#include <cstddef>
#include <tuple>
#include <type_traits>
#include <utility>

namespace coordinates {

struct Point {
  int x;
  int y;
};

template <std::size_t Index>
int& get(Point& point) {
  static_assert(Index < 2);
  if constexpr (Index == 0) {
    return point.x;
  } else {
    return point.y;
  }
}

template <std::size_t Index>
const int& get(const Point& point) {
  static_assert(Index < 2);
  if constexpr (Index == 0) {
    return point.x;
  } else {
    return point.y;
  }
}

template <std::size_t Index>
int&& get(Point&& point) {
  return std::move(get<Index>(point));
}

}  // namespace coordinates

template <>
struct std::tuple_size<coordinates::Point> : std::integral_constant<std::size_t, 2> {};

template <std::size_t Index>
struct std::tuple_element<Index, coordinates::Point> {
  static_assert(Index < 2);
  using type = int;
};

namespace {

enum LegacyState {
  legacy_idle,
  legacy_running,
};

enum class StrongState : unsigned char {
  idle = 1,
  running = 2,
};

struct TextHeader {
  unsigned int kind;
  char marker;
};

struct NumberHeader {
  unsigned int kind;
  double value;
};

union Message {
  TextHeader text;
  NumberHeader number;
};

struct Permissions {
  unsigned int read : 1;
  unsigned int write : 1;
  unsigned int execute : 1;
};

TEST(StructuredBindings, ArrayBindingCopiesUnlessTheHiddenObjectIsAReference) {
  std::array<int, 2> values{3, 5};

  auto [copy_first, copy_second] = values;
  auto& [alias_first, alias_second] = values;

  copy_first = 30;
  alias_second = 50;

  EXPECT_EQ(copy_first, 30);
  EXPECT_EQ(copy_second, 5);
  EXPECT_EQ(values, (std::array<int, 2>{3, 50}));

  // structured binding 先创建一个隐藏对象 e；auto 会复制初始化 e，auto& 则让 e 引用
  // 原数组。各名字绑定 e 的元素，所以是否修改源对象首先由隐藏对象类型决定。
}

TEST(StructuredBindings, TupleProtocolUsesTupleSizeTupleElementAndAdlGet) {
  coordinates::Point point{7, 11};
  auto& [x, y] = point;

  static_assert(std::tuple_size_v<coordinates::Point> == 2);
  static_assert(std::is_same_v<decltype(x), int>);
  static_assert(std::is_same_v<decltype((x)), int&>);

  x += 1;
  y += 2;
  EXPECT_EQ(point.x, 8);
  EXPECT_EQ(point.y, 13);

  // tuple-like 分解由 tuple_size、tuple_element<I> 和 ADL 找到的 get<I> 协作完成。
  // decltype(name) 报告 tuple_element 类型，decltype((name)) 才显示表达式的引用类别。
}

TEST(Enumerations, ScopedEnumAvoidsNameLeakageAndImplicitIntegerConversion) {
  LegacyState legacy = legacy_running;
  StrongState strong = StrongState::running;

  EXPECT_EQ(legacy, 1);
  EXPECT_EQ(static_cast<unsigned int>(strong), 2U);
  static_assert(!std::is_convertible_v<StrongState, int>);
  static_assert(std::is_same_v<std::underlying_type_t<StrongState>, unsigned char>);

  // unscoped enum 的枚举器进入外围作用域并可隐式转整数；enum class 保留作用域且要求
  // 显式转换。固定底层类型还能稳定存储宽度，但不自动保证跨协议的有效枚举值集合。
}

TEST(Unions, OnlyTheActiveMemberMayNormallyBeRead) {
  Message message{.text = TextHeader{7, 'T'}};

  EXPECT_EQ(message.text.kind, 7U);
  EXPECT_EQ(message.text.marker, 'T');

  // text 是 active member，读取 number.value 会产生未定义行为。两个 standard-layout
  // 成员拥有 layout-compatible 的共同首成员 kind，因此允许通过 number.kind 检查标签。
  EXPECT_EQ(message.number.kind, 7U);

  message.number = NumberHeader{9, 3.5};
  EXPECT_EQ(message.number.kind, 9U);
  EXPECT_DOUBLE_EQ(message.number.value, 3.5);

  // 手工 union 需要调用者维护 active member 和非平凡对象生命周期；普通业务代码通常
  // 应优先使用 std::variant，让标签和销毁逻辑保持一致。
}

TEST(BitFields, WidthLimitsStoredValuesAndPreventsTakingAnOrdinaryReference) {
  Permissions permissions{1, 0, 1};

  EXPECT_EQ(permissions.read, 1U);
  EXPECT_EQ(permissions.write, 0U);
  EXPECT_EQ(permissions.execute, 1U);

  auto read_copy = permissions.read;
  read_copy = 0;
  EXPECT_EQ(read_copy, 0U);
  EXPECT_EQ(permissions.read, 1U);

  // bit-field 不是独立可寻址对象，不能取得地址或绑定普通非常量引用。字段布局、对齐和
  // 是否跨存储单元都是实现定义的，不能把 C++ bit-field 当成稳定的网络或磁盘格式。
}

}  // namespace
