// polyglot-covers:
// - cpp.stdlib.ranges.filter-view-lazy-predicate-evaluation
// - cpp.stdlib.ranges.filter-view-begin-cache-for-forward-range
// - cpp.stdlib.ranges.filter-view-reference-mutation
// - cpp.stdlib.ranges.filter-view-category-and-size-loss
// - cpp.stdlib.ranges.transform-view-lazy-invocation
// - cpp.stdlib.ranges.transform-view-value-versus-reference-result
// - cpp.stdlib.ranges.transform-view-preserved-size-and-navigation
// - cpp.stdlib.ranges.filter-transform-composition-order
// - cpp.stdlib.ranges.stateful-callable-lifetime-and-mutation

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <ranges>
#include <string>
#include <type_traits>
#include <vector>

namespace {

TEST(FilterView, PredicateRunsDuringTraversalRatherThanPipelineConstruction) {
  std::vector<int> values{1, 2, 3, 4};
  int calls = 0;
  auto evens = values | std::views::filter([&calls](int value) {
    ++calls;
    return value % 2 == 0;
  });

  EXPECT_EQ(calls, 0);
  auto first = evens.begin();
  EXPECT_EQ(*first, 2);
  EXPECT_EQ(calls, 2);

  ++first;
  EXPECT_EQ(*first, 4);
  EXPECT_EQ(calls, 4);

  // 构造 filter_view 只保存上游与 predicate；begin() 才扫描首个匹配项，++ 再扫描下一个。
  // 因此副作用发生次数取决于消费方式，不应把 predicate 当作恰好调用一次的通知回调。
}

TEST(FilterView, ForwardRangeMayCacheTheFirstMatchingIterator) {
  std::vector<int> values{1, 2, 3, 4};
  int calls = 0;
  auto evens = values | std::views::filter([&calls](int value) {
    ++calls;
    return value % 2 == 0;
  });

  auto first = evens.begin();
  const int after_first_begin = calls;
  auto same_first = evens.begin();

  EXPECT_EQ(*first, 2);
  EXPECT_EQ(same_first, first);
  EXPECT_EQ(calls, after_first_begin);

  // 对 forward_range，filter_view 可缓存第一次 begin 的搜索结果，使重复 begin 为摊销常数。
  // 若底层元素或 predicate 依赖状态改变，旧缓存不会自动重新筛选；必要时重建 view。
}

TEST(FilterView, DereferenceReturnsTheUnderlyingReferenceAndAllowsMutation) {
  std::vector<int> values{1, 2, 3, 4};
  auto evens = values | std::views::filter([](int value) {
    return value % 2 == 0;
  });

  static_assert(std::is_same_v<std::ranges::range_reference_t<decltype(evens)>, int&>);
  for (int& value : evens) {
    value *= 10;
  }

  EXPECT_EQ(values, (std::vector<int>{1, 20, 3, 40}));

  // filter 只跳过元素，不生成新值，解引用仍是底层 int&。修改若使元素不再满足
  // predicate，已取得 iterator 不会被自动重新排列；遍历中改变筛选条件要格外谨慎。
}

TEST(FilterView, ItPreservesBidirectionalTraversalButCannotBeRandomAccessOrSized) {
  std::vector<int> values{1, 2, 3, 4};
  auto evens = values | std::views::filter([](int value) {
    return value % 2 == 0;
  });

  static_assert(std::ranges::bidirectional_range<decltype(evens)>);
  static_assert(!std::ranges::random_access_range<decltype(evens)>);
  static_assert(!std::ranges::sized_range<decltype(evens)>);

  auto iterator = evens.end();
  --iterator;
  EXPECT_EQ(*iterator, 4);

  // 即使底层 vector 可随机访问且有 size，第 n 个匹配项仍需扫描，匹配数量也需计算；
  // filter 因而最多保留双向遍历，不承诺 random access 或 sized_range。
}

TEST(TransformView, CallableRunsOnlyWhenAnElementIsDereferenced) {
  std::vector<int> values{1, 2, 3};
  int calls = 0;
  auto doubled = values | std::views::transform([&calls](int value) {
    ++calls;
    return value * 2;
  });

  EXPECT_EQ(calls, 0);
  auto iterator = doubled.begin();
  EXPECT_EQ(calls, 0);
  EXPECT_EQ(*iterator, 2);
  EXPECT_EQ(calls, 1);
  EXPECT_EQ(*iterator, 2);
  EXPECT_EQ(calls, 2);

  // transform iterator 通常在 operator* 时 invoke callable，不缓存变换值；重复解引用可能
  // 重复计算和副作用。需要稳定缓存时应显式物化结果，而不是依赖 view。
}

TEST(TransformView, ReturningAValueOrReferenceChangesWhetherWritesReachTheSource) {
  std::vector<int> values{1, 2, 3};
  auto values_view = values | std::views::transform([](int value) {
    return value * 10;
  });
  auto references_view = values | std::views::transform([](int& value) -> int& {
    return value;
  });

  static_assert(std::is_same_v<
                std::ranges::range_reference_t<decltype(values_view)>,
                int>);
  static_assert(std::is_same_v<
                std::ranges::range_reference_t<decltype(references_view)>,
                int&>);

  *references_view.begin() = 7;
  EXPECT_EQ(values.front(), 7);
  EXPECT_EQ(*values_view.begin(), 70);

  // transform 的 reference 类型就是 invoke_result；返回 prvalue 得到只读计算值，返回
  // T& 则可写回底层。不要从 adaptor 名字推断是否可修改，应检查 callable 返回类型。
}

TEST(TransformView, ItCanPreserveRandomAccessCommonAndSizedRangeProperties) {
  std::vector<int> values{1, 2, 3, 4};
  auto squares = values | std::views::transform([](int value) {
    return value * value;
  });

  static_assert(std::ranges::random_access_range<decltype(squares)>);
  static_assert(std::ranges::common_range<decltype(squares)>);
  static_assert(std::ranges::sized_range<decltype(squares)>);
  static_assert(!std::ranges::contiguous_range<decltype(squares)>);

  EXPECT_EQ(squares.size(), values.size());
  EXPECT_EQ(squares[2], 9);
  EXPECT_EQ(*(squares.end() - 1), 16);

  // 一对一变换不改变元素数量或位置，所以可保留 size 和随机访问；但解引用是计算结果，
  // 不再对应连续 T 存储地址，因此不能保留 contiguous_range。
}

TEST(ViewComposition, FilterBeforeTransformAndTransformBeforeFilterMeanDifferentQueries) {
  std::vector<int> values{1, 2, 3, 4};

  auto filter_then_transform = values |
                               std::views::filter([](int value) {
                                 return value % 2 == 0;
                               }) |
                               std::views::transform([](int value) {
                                 return value + 1;
                               });
  auto transform_then_filter = values |
                               std::views::transform([](int value) {
                                 return value + 1;
                               }) |
                               std::views::filter([](int value) {
                                 return value % 2 == 0;
                               });

  std::vector<int> first;
  std::vector<int> second;
  std::ranges::copy(filter_then_transform, std::back_inserter(first));
  std::ranges::copy(transform_then_filter, std::back_inserter(second));

  EXPECT_EQ(first, (std::vector<int>{3, 5}));
  EXPECT_EQ(second, (std::vector<int>{2, 4}));

  // 管道按左到右嵌套：先筛原值再 +1，与先 +1 再判断偶数不是等价优化。
  // 重排 adaptor 前必须证明 predicate 与 transform 的语义关系，而不只是看性能。
}

TEST(StatefulCallables, TheViewOwnsACopyUnlessTheCallableItselfCapturesReferences) {
  int factor = 3;
  auto multiplier = [factor](int value) {
    return value * factor;
  };
  std::vector<int> values{2};
  auto transformed = values | std::views::transform(multiplier);

  factor = 10;
  EXPECT_EQ(*transformed.begin(), 6);

  // adaptor 按值保存 multiplier，其中 factor 已复制为 3；之后修改外部变量无影响。
  // 若 lambda 使用 [&factor]，view 就保存间接引用，factor 必须活到最后一次遍历。
}

}  // namespace
