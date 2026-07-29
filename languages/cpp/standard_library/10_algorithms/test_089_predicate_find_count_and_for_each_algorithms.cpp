// polyglot-covers:
// - cpp.stdlib.algorithms.all-any-none-of-short-circuit
// - cpp.stdlib.algorithms.for-each-mutation-and-returned-function-state
// - cpp.stdlib.algorithms.ranges-for-each-result-input-and-function
// - cpp.stdlib.algorithms.algorithm-result-aggregate-and-converting-members
// - cpp.stdlib.algorithms.for-each-n-exact-prefix
// - cpp.stdlib.algorithms.find-and-ranges-find-projection
// - cpp.stdlib.algorithms.find-if-and-find-if-not
// - cpp.stdlib.algorithms.count-and-count-if
// - cpp.stdlib.algorithms.ranges-algorithm-dangling-temporary-result
// - cpp.stdlib.algorithms.function-object-must-not-invalidate-iterators

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <functional>
#include <ranges>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

struct Record {
  int id;
  std::string name;
  bool active;
};

struct SumValues {
  int total = 0;

  void operator()(int value) {
    total += value;
  }
};

TEST(PredicateAlgorithms, AllAnyAndNoneShortCircuitAtTheDecisiveElement) {
  const std::vector<int> values{2, 4, 5, 8};
  int all_calls = 0;
  const bool all_even = std::all_of(values.begin(), values.end(), [&](int value) {
    ++all_calls;
    return value % 2 == 0;
  });

  int any_calls = 0;
  const bool has_odd = std::ranges::any_of(values, [&](int value) {
    ++any_calls;
    return value % 2 != 0;
  });

  int none_calls = 0;
  const bool no_negative = std::ranges::none_of(values, [&](int value) {
    ++none_calls;
    return value < 0;
  });

  EXPECT_FALSE(all_even);
  EXPECT_TRUE(has_odd);
  EXPECT_TRUE(no_negative);
  EXPECT_EQ(all_calls, 3);
  EXPECT_EQ(any_calls, 3);
  EXPECT_EQ(none_calls, 4);

  // all_of 在首个 false 停止，any_of 在首个 true 停止，none_of 只有全为 false 才扫描完。
  // 空 range 上 all_of/none_of 为 true、any_of 为 false，符合逻辑量词的空集规则。
}

TEST(PredicateAlgorithms, EmptyRangeUsesVacuousTruthWithoutCallingThePredicate) {
  const std::vector<int> empty;
  int calls = 0;
  auto predicate = [&](int) {
    ++calls;
    return true;
  };

  EXPECT_TRUE(std::ranges::all_of(empty, predicate));
  EXPECT_FALSE(std::ranges::any_of(empty, predicate));
  EXPECT_TRUE(std::ranges::none_of(empty, predicate));
  EXPECT_EQ(calls, 0);

  // 空 range 没有可传给 predicate 的元素；all/none 的真值不是“默认调用一次”的结果。
}

TEST(ForEach, ClassicOverloadReturnsTheFinalFunctionObjectState) {
  const std::array<int, 4> values{1, 2, 3, 4};

  SumValues result = std::for_each(values.begin(), values.end(), SumValues{});

  EXPECT_EQ(result.total, 10);

  // 经典 for_each 按值接收函数对象并返回算法内部最终副本；若状态只存在该副本中，
  // 必须接住返回值。外部引用捕获则修改共享状态，两种所有权语义不要混淆。
}

TEST(ForEach, MutableElementReferencesCanUpdateValuesButMustNotInvalidateTraversal) {
  std::vector<int> values{1, 2, 3};

  std::ranges::for_each(values, [](int& value) {
    value *= 10;
  });

  EXPECT_EQ(values, (std::vector<int>{10, 20, 30}));

  // 非修改序列算法是指不重排 range 结构，callable 仍可通过 int& 修改元素值。
  // 回调中 push_back/erase 同一 vector 可能使算法持有的 iterator 失效，不能这样使用。
}

TEST(ForEach, RangesResultCarriesBothTheFinalIteratorAndFunction) {
  const std::array<int, 3> values{2, 3, 5};

  auto result = std::ranges::for_each(values, SumValues{});

  EXPECT_EQ(result.in, values.end());
  EXPECT_EQ(result.fun.total, 10);
  static_assert(std::is_same_v<decltype(result.fun), SumValues>);

  // ranges::for_each 返回 in_fun_result：in 是消费结束位置，fun 是最终函数对象。
  // 具名字段比 pair 的 first/second 更能表达算法结果，也支持转换到兼容结果类型。
}

TEST(AlgorithmResults, AggregateMembersConvertToCompatiblePositionTypes) {
  std::array<int, 2> input{1, 2};
  std::array<int, 2> output{};
  std::ranges::in_out_result<int*, int*> mutable_result{
      input.data() + 2,
      output.data() + 2,
  };

  std::ranges::in_out_result<const int*, const int*> const_result = mutable_result;
  auto [input_end, output_end] = const_result;

  static_assert(std::is_aggregate_v<decltype(mutable_result)>);
  EXPECT_EQ(input_end, input.data() + 2);
  EXPECT_EQ(output_end, output.data() + 2);

  // result 类是有具名字段的 aggregate，并提供受 convertible_to 约束的 const& 与 &&
  // 转换；可把可写 iterator 结果提升为只读 iterator 结果，不能反向丢掉 const。
}

TEST(ForEachN, ItProcessesExactlyNElementsStartingAtTheIterator) {
  std::array<int, 5> values{1, 2, 3, 4, 5};

  auto end = std::for_each_n(values.begin() + 1, 3, [](int& value) {
    value *= -1;
  });

  EXPECT_EQ(values, (std::array<int, 5>{1, -2, -3, -4, 5}));
  EXPECT_EQ(end, values.begin() + 4);

  // for_each_n 没有 sentinel 参数，调用者必须保证从 first 起至少有 n 个合法元素；
  // 返回 first+n。n 为负时经典 overload 的行为不适合作为边界裁剪工具。
}

TEST(Find, EqualitySearchReturnsFirstMatchOrEnd) {
  const std::vector<int> values{1, 2, 3, 2};

  auto first_two = std::find(values.begin(), values.end(), 2);
  auto missing = std::ranges::find(values, 9);

  EXPECT_EQ(first_two, values.begin() + 1);
  EXPECT_EQ(missing, values.end());

  // find 返回首个匹配位置，不统计全部匹配；失败用传入 range 的 end 表示，调用者必须
  // 在解引用前比较。需要数量用 count，需要所有位置应继续迭代或另建结果容器。
}

TEST(Find, RangesProjectionComparesASelectedMemberWithoutTransformingTheRange) {
  std::vector<Record> records{
      {1, "Ada", true},
      {2, "Bjarne", false},
      {3, "Grace", true},
  };

  auto found = std::ranges::find(records, 2, &Record::id);

  ASSERT_NE(found, records.end());
  EXPECT_EQ(found->name, "Bjarne");

  // projection 先对每个 Record 调用 &Record::id，再与 2 比较；返回 iterator 仍指向完整
  // Record。无需先构造 ids 临时容器，也不会丢失其他字段。
}

TEST(FindPredicates, FindIfAndFindIfNotExpressOppositeStoppingConditions) {
  const std::vector<Record> records{
      {1, "Ada", true},
      {2, "Bjarne", false},
      {3, "Grace", true},
  };

  auto inactive = std::ranges::find_if(records, std::logical_not<>{}, &Record::active);
  auto first_not_active = std::ranges::find_if_not(records, std::identity{}, &Record::active);

  ASSERT_NE(inactive, records.end());
  EXPECT_EQ(inactive, first_not_active);
  EXPECT_EQ(inactive->id, 2);

  // find_if_not 在 predicate 首次为 false 时停止；配合 identity 投影可直接查布尔成员。
  // 为可读性通常应选择能清楚表达业务条件的版本，而不是堆叠多层逻辑取反。
}

TEST(Count, EqualityAndPredicateFormsReturnSignedIteratorDifference) {
  const std::vector<Record> records{
      {1, "Ada", true},
      {2, "Bjarne", false},
      {3, "Grace", true},
  };

  const auto active = std::ranges::count(records, true, &Record::active);
  const auto long_names = std::ranges::count_if(records, [](const std::string& name) {
    return name.size() > 3;
  }, &Record::name);

  static_assert(std::is_signed_v<decltype(active)>);
  EXPECT_EQ(active, 2);
  EXPECT_EQ(long_names, 2);

  // count/count_if 必须扫描完整 range 才能得出数量，返回 range_difference_t 的有符号值，
  // 不是容器 size_type。projection 同样作用在比较/谓词之前。
}

TEST(RangesFind, TemporaryOwnedRangeReturnsDanglingInsteadOfAnInvalidIterator) {
  auto result = std::ranges::find(std::vector<int>{1, 2, 3}, 2);

  static_assert(std::is_same_v<decltype(result), std::ranges::dangling>);
  (void)result;

  // 算法确实完成查找，但临时 vector 在 full-expression 末销毁；borrowed_iterator_t
  // 把返回类型变为 dangling。需要 iterator 时先命名 owning range。
}

}  // namespace
