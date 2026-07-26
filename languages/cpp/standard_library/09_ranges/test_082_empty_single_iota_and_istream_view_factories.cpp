// polyglot-covers:
// - cpp.stdlib.ranges.empty-view-and-views-empty
// - cpp.stdlib.ranges.single-view-one-owned-element
// - cpp.stdlib.ranges.single-view-data-size-and-mutation
// - cpp.stdlib.ranges.iota-view-bounded-half-open-sequence
// - cpp.stdlib.ranges.iota-view-unbounded-and-unreachable-sentinel
// - cpp.stdlib.ranges.iota-view-iterator-strength-and-distance
// - cpp.stdlib.ranges.istream-view-formatted-single-pass-input
// - cpp.stdlib.ranges.range-factory-composition-with-adaptors

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <ranges>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

namespace {

TEST(EmptyView, ItIsAZeroLengthContiguousBorrowedRangeWithoutStorage) {
  auto empty = std::views::empty<int>;

  static_assert(std::is_same_v<decltype(empty), std::ranges::empty_view<int>>);
  static_assert(std::ranges::view<decltype(empty)>);
  static_assert(std::ranges::borrowed_range<decltype(empty)>);
  static_assert(std::ranges::contiguous_range<decltype(empty)>);
  static_assert(std::ranges::sized_range<decltype(empty)>);

  EXPECT_TRUE(empty.empty());
  EXPECT_EQ(empty.size(), 0U);
  EXPECT_EQ(empty.begin(), empty.end());

  // empty_view<T> 不拥有 T 对象，提供空指针边界和常数 size 0；views::empty<T> 是可复用
  // 的变量模板。不能解引用 begin，也不要从 data 的具体空指针表示推导额外语义。
}

TEST(SingleView, ItOwnsExactlyOneElementAndExposesContiguousAccess) {
  auto one = std::views::single(std::string{"payload"});

  static_assert(std::ranges::view<decltype(one)>);
  static_assert(std::ranges::contiguous_range<decltype(one)>);
  static_assert(std::ranges::sized_range<decltype(one)>);

  EXPECT_EQ(one.size(), 1U);
  EXPECT_EQ(one.front(), "payload");
  EXPECT_EQ(one.data(), &one.front());

  one.front() = "changed";
  EXPECT_EQ(*one.begin(), "changed");

  // single_view 按值拥有一个元素，与 span/ref_view 不同；复制 view 会复制该元素。
  // begin/end 是覆盖内部对象的连续范围，元素寿命跟随 single_view 对象。
}

TEST(SingleView, CopyingTheViewCreatesAnIndependentElement) {
  auto original = std::views::single(7);
  auto copied = original;

  copied.front() = 11;

  EXPECT_EQ(original.front(), 7);
  EXPECT_EQ(copied.front(), 11);

  // N4861 single_view 要求元素 copy_constructible，并使用半正则包装保存；复制不是别名。
  // 若想只查看外部单个对象，应使用 span<T,1> 等非拥有 view。
}

TEST(IotaView, BoundedFactoryProducesAHalfOpenArithmeticSequence) {
  auto values = std::views::iota(2, 7);
  std::vector<int> observed(values.begin(), values.end());

  EXPECT_EQ(observed, (std::vector<int>{2, 3, 4, 5, 6}));
  EXPECT_EQ(values.size(), 5U);
  EXPECT_EQ(values[2], 4);

  // iota(value,bound) 生成 [value,bound)，不包含 bound；对整数提供 sized、common、
  // random-access range。若起点大于终点却仍按 ++ 方向生成，结束条件可能永远达不到。
}

TEST(IotaView, IteratorArithmeticAndDistanceFollowTheIncrementableValue) {
  auto letters = std::views::iota('a', 'f');
  auto iterator = letters.begin();

  static_assert(std::ranges::random_access_range<decltype(letters)>);
  static_assert(std::ranges::common_range<decltype(letters)>);
  static_assert(std::ranges::sized_range<decltype(letters)>);

  iterator += 3;
  EXPECT_EQ(*iterator, 'd');
  EXPECT_EQ(letters.end() - iterator, 2);
  EXPECT_EQ(std::ranges::distance(letters), 5);

  // iterator 能力取决于 W 的增减、差值与排序运算；整数 iota 可常数时间跳转。
  // 解引用返回当前计数值而非外部容器引用，修改该结果不会写回某个存储元素。
}

TEST(IotaView, OneArgumentFactoryUsesUnreachableSentinelForAnUnboundedSequence) {
  auto naturals = std::views::iota(10);
  auto first_four = naturals | std::views::take(4);
  std::vector<int> observed;
  std::ranges::copy(first_four, std::back_inserter(observed));

  static_assert(!std::ranges::common_range<decltype(naturals)>);
  static_assert(!std::ranges::sized_range<decltype(naturals)>);
  EXPECT_EQ(observed, (std::vector<int>{10, 11, 12, 13}));

  // 单参数 iota 的 end 是 unreachable_sentinel，无界 distance 或完整遍历不会终止；
  // 应先组合 take/take_while 等有限边界。本例只消费四项。
}

TEST(IstreamView, ItUsesFormattedExtractionAndModelsOnlyInputRange) {
  std::istringstream input{"3 5 invalid 7"};
  auto values = std::ranges::istream_view<int>(input);
  std::vector<int> observed;

  static_assert(std::ranges::input_range<decltype(values)>);
  static_assert(!std::ranges::forward_range<decltype(values)>);
  static_assert(!std::ranges::common_range<decltype(values)>);

  for (int value : values) {
    observed.push_back(value);
  }

  EXPECT_EQ(observed, (std::vector<int>{3, 5}));
  EXPECT_TRUE(input.fail());

  // istream_view 与 istream_iterator 一样调用 operator>>，解析失败就结束；iterator 共享
  // stream 的消费状态，只是 input range。view 保存 stream 指针，不拥有 stream。
}

TEST(RangeFactories, FactoriesComposeLazilyWithoutMaterializingIntermediateContainers) {
  auto pipeline = std::views::iota(1, 20) |
                  std::views::filter([](int value) {
                    return value % 2 == 0;
                  }) |
                  std::views::transform([](int value) {
                    return value * value;
                  }) |
                  std::views::take(3);
  std::vector<int> observed;
  std::ranges::copy(pipeline, std::back_inserter(observed));

  EXPECT_EQ(observed, (std::vector<int>{4, 16, 36}));

  // 每层只保存前一层 view 与函数对象，遍历时才筛选和变换；没有中间 vector。
  // 惰性也意味着捕获的引用和底层 range 必须活到 pipeline 消费结束。
}

}  // namespace
