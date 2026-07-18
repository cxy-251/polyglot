// polyglot-covers:
// - cpp.stdlib.ranges.take-view-count-clamped-to-range-size
// - cpp.stdlib.ranges.take-view-preserved-random-access-and-size
// - cpp.stdlib.ranges.take-view-bounds-unbounded-range
// - cpp.stdlib.ranges.take-while-stops-before-first-failure
// - cpp.stdlib.ranges.take-while-unsized-sentinel-and-lazy-predicate
// - cpp.stdlib.ranges.drop-view-count-clamped-to-range-size
// - cpp.stdlib.ranges.drop-view-preserved-reference-and-navigation
// - cpp.stdlib.ranges.drop-while-removes-only-leading-matches
// - cpp.stdlib.ranges.drop-while-begin-cache-and-state-change
// - cpp.stdlib.ranges.take-drop-zero-and-empty-results

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <ranges>
#include <vector>

namespace {

template <std::ranges::input_range Range>
std::vector<std::ranges::range_value_t<Range>> Collect(Range&& range) {
  std::vector<std::ranges::range_value_t<Range>> result;
  std::ranges::copy(range, std::back_inserter(result));
  return result;
}

TEST(TakeView, CountIsClampedToTheAvailableSizedRange) {
  std::vector<int> values{1, 2, 3};
  auto first_two = values | std::views::take(2);
  auto more_than_all = values | std::views::take(20);

  EXPECT_EQ(Collect(first_two), (std::vector<int>{1, 2}));
  EXPECT_EQ(Collect(more_than_all), values);
  EXPECT_EQ(first_two.size(), 2U);
  EXPECT_EQ(more_than_all.size(), values.size());

  // 对 sized_range，take 的逻辑长度是 min(count,size)，count 超过剩余元素不会越界。
  // count 必须非负；负数违反 adaptor 的前置条件，不应拿来表达“去掉末尾”。
}

TEST(TakeView, RandomAccessSizedInputKeepsEfficientNavigation) {
  std::vector<int> values{2, 3, 5, 7};
  auto first_three = values | std::views::take(3);

  static_assert(std::ranges::random_access_range<decltype(first_three)>);
  static_assert(std::ranges::sized_range<decltype(first_three)>);
  static_assert(std::ranges::common_range<decltype(first_three)>);

  EXPECT_EQ(first_three[2], 5);
  first_three[1] = 30;
  EXPECT_EQ(values[1], 30);

  // take 不变换元素，reference 仍来自底层；对 sized random-access range 可直接计算 end，
  // 因而保留随机访问、size 和 common range。较弱输入则可能使用 counted sentinel。
}

TEST(TakeView, ItTurnsAnUnboundedIotaIntoAFiniteRange) {
  auto unbounded = std::views::iota(10);
  auto first_four = unbounded | std::views::take(4);

  EXPECT_EQ(Collect(first_four), (std::vector<int>{10, 11, 12, 13}));
  EXPECT_EQ(std::ranges::distance(first_four), 4);

  // 单参数 iota 的 sentinel 永不可达，take 用 count 提供外层终止条件；这也是消费无限
  // generator 的常见方式。不要先对 unbounded 调用 distance 再决定 take 数量。
}

TEST(TakeWhileView, ItStopsBeforeTheFirstPredicateFailure) {
  std::vector<int> values{2, 4, 5, 6, 8};
  auto leading_even = values | std::views::take_while([](int value) {
    return value % 2 == 0;
  });

  EXPECT_EQ(Collect(leading_even), (std::vector<int>{2, 4}));

  // take_while 取得满足 predicate 的连续前缀，遇到 5 后永久结束；后面的 6、8 即使
  // 满足也不会出现。若想保留所有偶数应使用 filter，而不是 take_while。
}

TEST(TakeWhileView, PredicateIsLazyAndTheEndIsUsuallyADifferentSentinel) {
  std::vector<int> values{1, 2, 3, 4};
  int calls = 0;
  auto below_three = values | std::views::take_while([&calls](int value) {
    ++calls;
    return value < 3;
  });

  EXPECT_EQ(calls, 0);
  EXPECT_EQ(Collect(below_three), (std::vector<int>{1, 2}));
  EXPECT_EQ(calls, 3);

  static_assert(!std::ranges::sized_range<decltype(below_three)>);
  static_assert(!std::ranges::common_range<decltype(below_three)>);

  // sentinel 比较时调用 predicate，所以连首个失败元素也要检查一次。结束位置需扫描才
  // 知道，通常不再 sized/common；即使底层 vector 拥有这些性质也不会保留。
}

TEST(DropView, CountIsClampedAndTheRemainderKeepsOriginalOrder) {
  std::vector<int> values{1, 2, 3, 4};
  auto after_two = values | std::views::drop(2);
  auto after_all = values | std::views::drop(20);

  EXPECT_EQ(Collect(after_two), (std::vector<int>{3, 4}));
  EXPECT_TRUE(after_all.empty());
  EXPECT_EQ(after_two.size(), 2U);
  EXPECT_EQ(after_all.size(), 0U);

  // drop 跳过 min(count,size) 个元素，过大的 count 得到空 view，不会把 begin 推过 end。
  // 它不复制被保留元素，底层结构变化仍可能使 view 的 iterator/cache 失效。
}

TEST(DropView, RandomAccessInputKeepsSizeNavigationAndWritableReferences) {
  std::vector<int> values{2, 3, 5, 7};
  auto tail = values | std::views::drop(1);

  static_assert(std::ranges::random_access_range<decltype(tail)>);
  static_assert(std::ranges::sized_range<decltype(tail)>);
  static_assert(std::ranges::common_range<decltype(tail)>);

  EXPECT_EQ(tail[0], 3);
  tail[1] = 50;
  EXPECT_EQ(values[2], 50);

  // 对 random-access sized range，drop 的 begin 可常数时间计算并保留底层类别；
  // reference 仍是 int&。drop 只改变可见起点，不建立独立尾部容器。
}

TEST(DropWhileView, ItRemovesOnlyTheLeadingMatchingPrefix) {
  std::vector<int> values{2, 4, 5, 6, 8};
  auto from_first_odd = values | std::views::drop_while([](int value) {
    return value % 2 == 0;
  });

  EXPECT_EQ(Collect(from_first_odd), (std::vector<int>{5, 6, 8}));

  // drop_while 找到第一个 predicate==false 的元素后，后续全部原样保留；它不会继续
  // 删除 6、8。表达“删除所有偶数”应使用 filter 的相反谓词。
}

TEST(DropWhileView, ForwardRangeCachesItsDiscoveredBeginPosition) {
  std::vector<int> values{1, 2, 3, 4};
  int threshold = 3;
  int calls = 0;
  auto tail = values | std::views::drop_while([&](int value) {
    ++calls;
    return value < threshold;
  });

  auto first = tail.begin();
  const int after_first = calls;
  EXPECT_EQ(*first, 3);

  threshold = 1;
  auto cached = tail.begin();
  EXPECT_EQ(cached, first);
  EXPECT_EQ(calls, after_first);

  // forward_range 的 drop_while_view 缓存首次搜索得到的 begin。改变 predicate 依赖状态
  // 不会清缓存；若需要按新 threshold 重新选择前缀，应重新构造 view。
}

TEST(PrefixViews, ZeroCountsAndImmediateFailuresProduceWellDefinedEdges) {
  std::vector<int> values{1, 2, 3};
  auto take_none = values | std::views::take(0);
  auto drop_none = values | std::views::drop(0);
  auto take_failure = values | std::views::take_while([](int) {
    return false;
  });
  auto drop_failure = values | std::views::drop_while([](int) {
    return false;
  });

  EXPECT_TRUE(take_none.empty());
  EXPECT_EQ(Collect(drop_none), values);
  EXPECT_TRUE(take_failure.empty());
  EXPECT_EQ(Collect(drop_failure), values);

  // count==0 与 predicate 首项失败都是正常边界：take 为空，drop 保留全部。
  // 空 view 的 begin==end，不能因底层非空就解引用。
}

}  // namespace
