// polyglot-covers:
// - cpp.stdlib.ranges.views-all-existing-view-and-lvalue-range
// - cpp.stdlib.ranges.ref-view-non-owning-lvalue-alias
// - cpp.stdlib.ranges.all-t-normalized-view-type
// - cpp.stdlib.ranges.viewable-range-temporary-owning-version-evolution
// - cpp.stdlib.ranges.range-adaptor-object-pipe-syntax
// - cpp.stdlib.ranges.range-adaptor-partial-application
// - cpp.stdlib.ranges.range-adaptor-closure-composition-and-reuse
// - cpp.stdlib.ranges.lazy-view-reference-and-callable-lifetime

#include <gtest/gtest.h>

#include <algorithm>
#include <concepts>
#include <iterator>
#include <ranges>
#include <span>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

template <class Range>
concept CanAll = requires {
  std::views::all(std::declval<Range>());
};

TEST(AllView, ExistingViewsStayViewsAndLvalueContainersBecomeRefViews) {
  std::vector<int> values{1, 2, 3};
  auto from_lvalue = std::views::all(values);
  std::span<int> span{values};
  auto from_view = std::views::all(span);

  static_assert(std::is_same_v<
                decltype(from_lvalue),
                std::ranges::ref_view<std::vector<int>>>);
  static_assert(std::is_same_v<decltype(from_view), std::span<int>>);

  from_lvalue.front() = 10;
  from_view[1] = 20;
  EXPECT_EQ(values, (std::vector<int>{10, 20, 3}));

  // views::all 规范化输入：可复制 view 按值保存，普通 lvalue range 用 ref_view 包装。
  // 两条路径都不复制 vector 元素；ref_view 和 span 的修改写回同一底层容器。
}

TEST(RefView, ItRequiresAnLvalueAndExposesTheReferencedRange) {
  std::vector<int> values{2, 3, 5};
  std::ranges::ref_view view{values};

  static_assert(std::ranges::borrowed_range<decltype(view)>);
  static_assert(!std::is_constructible_v<
                std::ranges::ref_view<std::vector<int>>,
                std::vector<int>&&>);

  EXPECT_EQ(&view.base(), &values);
  EXPECT_EQ(view.size(), values.size());
  view.back() = 7;
  EXPECT_EQ(values.back(), 7);

  // ref_view 内部只有指向 lvalue range 的引用语义，base() 返回原对象；构造时拒绝临时
  // range，避免包装完成时底层已销毁。view 本身 borrowed，但 values 仍须存活。
}

TEST(AllView, AllTypeAliasDescribesTheNormalizedAdaptorResult) {
  using Container = std::vector<int>;
  using LvalueAll = std::views::all_t<Container&>;
  using SpanAll = std::views::all_t<std::span<int>>;

  static_assert(std::is_same_v<LvalueAll, std::ranges::ref_view<Container>>);
  static_assert(std::is_same_v<SpanAll, std::span<int>>);

  // all_t<R> 等价于 decltype(views::all(declval<R>()))，便于其他 view 在类型层统一保存
  // 上游 range，而不必自己重复 view/ref 包装选择逻辑。
}

TEST(AllView, TemporaryOwnedRangeAcceptanceDependsOnAppliedStandardRepair) {
  [[maybe_unused]] constexpr bool accepts_temporary_vector =
      CanAll<std::vector<int>&&>;

  // 原始 N4861 的 viewable_range 拒绝非 borrowed 的临时 vector；后续标准修订增加拥有型
  // 包装，部分实现会回溯。这里的 requires 表达式是能力检测，不按编译器版本猜测，
  // 也不通过构造兼容包装伪造当前实现尚未提供的路径。
}

TEST(RangeAdaptorObjects, PipeSyntaxPassesTheLeftRangeIntoTheAdaptor) {
  std::vector<int> values{1, 2, 3, 4, 5, 6};
  auto result = values |
                std::views::filter([](int value) {
                  return value % 2 == 0;
                }) |
                std::views::transform([](int value) {
                  return value * 10;
                });

  std::vector<int> observed;
  std::ranges::copy(result, std::back_inserter(observed));
  EXPECT_EQ(observed, (std::vector<int>{20, 40, 60}));

  // `range | adaptor(args...)` 等价于把 range 交给已部分应用的 range adaptor object。
  // 返回的是惰性 view，filter/transform 不在管道构造时遍历 values。
}

TEST(RangeAdaptorObjects, PartialApplicationCreatesAReusableClosure) {
  auto first_two = std::views::take(2);
  std::vector<int> first_source{1, 2, 3};
  std::vector<int> second_source{4, 5, 6};

  auto first = first_source | first_two;
  auto second = second_source | first_two;

  EXPECT_EQ(std::vector<int>(first.begin(), first.end()),
            (std::vector<int>{1, 2}));
  EXPECT_EQ(std::vector<int>(second.begin(), second.end()),
            (std::vector<int>{4, 5}));

  // 缺少 range 参数时，adaptor 保存其余参数并成为 closure，可应用到多个 range。
  // closure 不缓存第一次遍历结果，每次仍引用各自的底层 source。
}

TEST(RangeAdaptorObjects, ClosuresCanBeComposedBeforeARangeIsAvailable) {
  auto positive_squares =
      std::views::filter([](int value) {
        return value > 0;
      }) |
      std::views::transform([](int value) {
        return value * value;
      });

  std::vector<int> values{-2, 1, -1, 3};
  auto result = values | positive_squares;
  std::vector<int> observed;
  std::ranges::copy(result, std::back_inserter(observed));

  EXPECT_EQ(observed, (std::vector<int>{1, 9}));

  // closure | closure 先组合处理步骤，之后再接 range；适合复用查询规则。
  // 每个闭包按值保存函数对象，捕获对象的复制/移动能力会影响组合是否可构造。
}

TEST(LazyViews, ReferencedStateMustOutliveEveryLaterIteration) {
  std::vector<int> values{1, 2, 3, 4};
  int threshold = 2;
  auto above = values | std::views::filter([&threshold](int value) {
    return value > threshold;
  });

  EXPECT_EQ(*above.begin(), 3);
  threshold = 3;

  auto rebuilt = values | std::views::filter([&threshold](int value) {
    return value > threshold;
  });
  EXPECT_EQ(*rebuilt.begin(), 4);

  // view 保存对 values 的引用，predicate 又捕获 threshold 引用；两者都必须活到遍历结束。
  // filter_view 还可缓存 begin，修改谓词依赖后最好重建 view，不能假设已有缓存自动失效。
}

}  // namespace
