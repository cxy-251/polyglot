// polyglot-covers:
// - cpp.stdlib.valarray.construction-copy-assignment-resize-and-swap
// - cpp.stdlib.valarray.unchecked-element-access-and-contiguous-range-access
// - cpp.stdlib.valarray.elementwise-arithmetic-scalar-and-comparison-operations
// - cpp.stdlib.valarray.expression-materialization-and-aliasing-caution
// - cpp.stdlib.valarray.sum-min-max-apply-shift-and-cshift
// - cpp.stdlib.valarray.elementwise-transcendental-functions
// - cpp.stdlib.valarray.slice-selection-and-slice-array-assignment
// - cpp.stdlib.valarray.gslice-multidimensional-strides
// - cpp.stdlib.valarray.mask-array-conditional-selection
// - cpp.stdlib.valarray.indirect-array-index-selection
// - cpp.stdlib.valarray.const-subset-copy-versus-nonconst-proxy
// - cpp.stdlib.valarray.proxy-lifetime-and-overlap-traps

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iterator>
#include <type_traits>
#include <utility>
#include <valarray>
#include <vector>

namespace {

template <class T>
std::vector<T> ToVector(const std::valarray<T>& values) {
  return std::vector<T>(std::begin(values), std::end(values));
}

TEST(ValarrayConstruction, CommonConstructorsBuildOwnedNumericArrays) {
  const std::valarray<int> empty;
  const std::valarray<int> repeated(7, 4);
  const int source[] = {1, 2, 3};
  const std::valarray<int> copied_from_pointer{source, 3};
  const std::valarray<int> initialized{4, 5, 6};

  EXPECT_EQ(empty.size(), 0U);
  EXPECT_EQ(ToVector(repeated), (std::vector<int>{7, 7, 7, 7}));
  EXPECT_EQ(ToVector(copied_from_pointer), (std::vector<int>{1, 2, 3}));
  EXPECT_EQ(ToVector(initialized), (std::vector<int>{4, 5, 6}));

  // `(value,count)` 必须注意与 initializer_list 的重载选择；下一个测试专门展示区别。
}

TEST(ValarrayConstruction, TwoArgumentValueConstructorNeedsParenthesesToAvoidListBias) {
  const std::valarray<int> repeated(7, 4);
  const std::valarray<int> two_elements{7, 4};

  EXPECT_EQ(ToVector(repeated), (std::vector<int>{7, 7, 7, 7}));
  EXPECT_EQ(ToVector(two_elements), (std::vector<int>{7, 4}));
}

TEST(ValarrayAssignment, CopyAssignmentAdoptsTheSourceSizeAndValues) {
  std::valarray<int> destination{9};
  const std::valarray<int> source{1, 2, 3};

  destination = source;

  EXPECT_EQ(ToVector(destination), (std::vector<int>{1, 2, 3}));
  destination = 5;
  EXPECT_EQ(ToVector(destination), (std::vector<int>{5, 5, 5}));

  // 标量赋值逐元素填充但不改大小；valarray 赋值可让目标采用源的大小。
}

TEST(ValarrayAssignment, ResizeReinitializesRatherThanPreservingAPrefix) {
  std::valarray<int> values{1, 2, 3};
  values.resize(5, 9);

  EXPECT_EQ(ToVector(values), (std::vector<int>{9, 9, 9, 9, 9}));

  values.resize(2);
  EXPECT_EQ(ToVector(values), (std::vector<int>{0, 0}));

  // valarray::resize 会使旧元素失效，并把所有新元素初始化为 c；它不像 vector::resize
  // 那样承诺保留共同前缀。
}

TEST(ValarrayAssignment, SwapExchangesWholeOwnedArrays) {
  std::valarray<int> left{1, 2};
  std::valarray<int> right{7, 8, 9};

  left.swap(right);

  EXPECT_EQ(ToVector(left), (std::vector<int>{7, 8, 9}));
  EXPECT_EQ(ToVector(right), (std::vector<int>{1, 2}));
}

TEST(ValarrayAccess, IndexingIsUncheckedButRangeAccessSupportsAlgorithms) {
  std::valarray<int> values{3, 1, 2};
  values[1] = 4;
  std::sort(std::begin(values), std::end(values));

  EXPECT_EQ(ToVector(values), (std::vector<int>{2, 3, 4}));
  EXPECT_EQ(std::distance(std::begin(values), std::end(values)), 3);

  // operator[] 没有 at() 式边界检查，越界不是可测试异常。C++11 的非成员 begin/end
  // 允许把 valarray 交给普通迭代器算法，并要求元素连续排列。
}

TEST(ValarrayArithmetic, ArrayAndScalarOperatorsWorkElementByElement) {
  const std::valarray<int> left{1, 2, 3};
  const std::valarray<int> right{4, 5, 6};
  const std::valarray<int> sum = left + right;
  const std::valarray<int> scaled = 2 * left + 1;
  const std::valarray<int> products = left * right;

  EXPECT_EQ(ToVector(sum), (std::vector<int>{5, 7, 9}));
  EXPECT_EQ(ToVector(scaled), (std::vector<int>{3, 5, 7}));
  EXPECT_EQ(ToVector(products), (std::vector<int>{4, 10, 18}));

  // 两个 valarray 参与二元运算时大小必须相同。实现可以用表达式模板延迟计算；需要保存
  // 独立结果时像这里一样显式物化为 valarray，而不是长期保存实现相关的 `auto` 表达式。
}

TEST(ValarrayArithmetic, CompoundAndUnaryOperatorsMutateOrTransformElements) {
  std::valarray<int> values{1, -2, 3};
  values += 2;
  values *= std::valarray<int>{2, 3, 4};

  const std::valarray<int> negated = -values;
  const std::valarray<int> bitwise_not = ~values;

  EXPECT_EQ(ToVector(values), (std::vector<int>{6, 0, 20}));
  EXPECT_EQ(ToVector(negated), (std::vector<int>{-6, 0, -20}));
  EXPECT_EQ(bitwise_not[0], ~6);
}

TEST(ValarrayComparison, ComparisonsProduceAValarrayOfBool) {
  const std::valarray<int> values{1, 4, 2, 5};
  const std::valarray<bool> greater_than_two = values > 2;
  const std::valarray<bool> even = (values % 2) == 0;
  const std::valarray<bool> selected = greater_than_two && even;

  EXPECT_EQ(ToVector(greater_than_two),
            (std::vector<bool>{false, true, false, true}));
  EXPECT_EQ(ToVector(even),
            (std::vector<bool>{false, true, true, false}));
  EXPECT_EQ(ToVector(selected),
            (std::vector<bool>{false, true, false, false}));

  // 结果是逐元素布尔数组，不会像容器 operator== 那样产生一个“整体是否相等”的 bool。
}

TEST(ValarrayMembers, ReductionsAndApplyCoverWholeArrayWorkflows) {
  const std::valarray<int> values{3, 1, 4, 2};
  const std::valarray<int> squared = values.apply([](int value) {
    return value * value;
  });

  EXPECT_EQ(values.sum(), 10);
  EXPECT_EQ(values.min(), 1);
  EXPECT_EQ(values.max(), 4);
  EXPECT_EQ(ToVector(squared), (std::vector<int>{9, 1, 16, 4}));

  // min/max 对空 valarray 没有有效前置条件，调用前必须先判断 size。apply 接收规定形式
  // 的函数指针，捕获 lambda 不能隐式转换为该接口。
}

TEST(ValarrayShift, ShiftFillsVacatedElementsAndCshiftWrapsThem) {
  const std::valarray<int> values{1, 2, 3, 4};

  EXPECT_EQ(ToVector(values.shift(2)), (std::vector<int>{3, 4, 0, 0}));
  EXPECT_EQ(ToVector(values.shift(-1)), (std::vector<int>{0, 1, 2, 3}));
  EXPECT_EQ(ToVector(values.cshift(1)), (std::vector<int>{2, 3, 4, 1}));
  EXPECT_EQ(ToVector(values.cshift(-1)), (std::vector<int>{4, 1, 2, 3}));

  // 正参数把后面的元素移到较小索引。shift 用 T{} 填空位；cshift 做循环移位，不丢元素。
}

TEST(ValarrayMath, StandardMathFunctionsTransformEveryElement) {
  const std::valarray<double> values{0.0, 1.0, 4.0};
  const std::valarray<double> roots = std::sqrt(values);
  const std::valarray<double> powers = std::pow(values, 2.0);
  const std::valarray<double> exponentials = std::exp(values);

  EXPECT_EQ(ToVector(roots), (std::vector<double>{0.0, 1.0, 2.0}));
  EXPECT_EQ(ToVector(powers), (std::vector<double>{0.0, 1.0, 16.0}));
  EXPECT_NEAR(exponentials[0], 1.0, 1e-12);
  EXPECT_NEAR(exponentials[1], std::exp(1.0), 1e-12);

  const std::valarray<double> angles{0.0, std::acos(-1.0) / 2.0};
  const std::valarray<double> sines = std::sin(angles);
  EXPECT_NEAR(sines[0], 0.0, 1e-12);
  EXPECT_NEAR(sines[1], 1.0, 1e-12);
}

TEST(ValarraySlice, SliceSelectsStartCountAndConstantStride) {
  std::valarray<int> values{0, 1, 2, 3, 4, 5, 6, 7};
  const std::slice evens{0, 4, 2};

  values[evens] = 9;
  EXPECT_EQ(ToVector(values),
            (std::vector<int>{9, 1, 9, 3, 9, 5, 9, 7}));

  values[evens] += std::valarray<int>{1, 2, 3, 4};
  EXPECT_EQ(ToVector(values),
            (std::vector<int>{10, 1, 11, 3, 12, 5, 13, 7}));

  // slice(start,size,stride) 的第二项是元素数量而非结束索引。非 const operator[] 返回
  // slice_array 代理，赋值和复合赋值会写回原数组。
}

TEST(ValarrayGeneralizedSlice, GsliceCombinesMultipleDimensionsAndStrides) {
  std::valarray<int> matrix{
      0, 1, 2, 3,
      4, 5, 6, 7,
      8, 9, 10, 11,
  };
  const std::valarray<std::size_t> sizes{2, 2};
  const std::valarray<std::size_t> strides{4, 2};
  const std::gslice every_other_column_in_first_two_rows{1, sizes, strides};

  matrix[every_other_column_in_first_two_rows] = -1;

  EXPECT_EQ(ToVector(matrix),
            (std::vector<int>{0, -1, 2, -1, 4, -1, 6, -1, 8, 9, 10, 11}));

  // 索引为 start + Σ(index[d]*stride[d])。这里选中 1、3、5、7；size/stride 数组
  // 长度必须一致，并由调用者保证所有生成索引有效。
}

TEST(ValarrayMask, BooleanMaskSelectsCorrespondingTruePositions) {
  std::valarray<int> values{10, 20, 30, 40, 50};
  const std::valarray<bool> mask{true, false, true, false, true};

  const std::valarray<int> copied = std::as_const(values)[mask];
  EXPECT_EQ(ToVector(copied), (std::vector<int>{10, 30, 50}));

  values[mask] = std::valarray<int>{1, 2, 3};
  EXPECT_EQ(ToVector(values), (std::vector<int>{1, 20, 2, 40, 3}));

  // mask 大小必须与源数组一致，右侧数组大小必须等于 true 的数量；接口不替调用者做
  // 边界或长度诊断。
}

TEST(ValarrayIndirect, IndexArrayControlsOrderAndMayRepeatPositions) {
  std::valarray<int> values{10, 20, 30, 40};
  const std::valarray<std::size_t> indices{3, 1, 3};

  const std::valarray<int> copied = std::as_const(values)[indices];
  EXPECT_EQ(ToVector(copied), (std::vector<int>{40, 20, 40}));

  const std::valarray<std::size_t> unique_indices{3, 1};
  values[unique_indices] = std::valarray<int>{7, 8};
  EXPECT_EQ(ToVector(values), (std::vector<int>{10, 8, 30, 7}));

  // 间接读取可重复、重排索引。写入代理若包含重复索引，多个赋值对同一元素的效果不宜
  // 依赖；需要确定行为时先去重或显式规定更新顺序。
}

TEST(ValarraySubsets, ConstAccessMaterializesButMutableAccessReturnsAProxy) {
  std::valarray<int> mutable_values{1, 2, 3, 4};
  const std::valarray<int>& const_values = mutable_values;
  const std::slice selection{0, 2, 2};

  auto mutable_selection = mutable_values[selection];
  const std::valarray<int> copied_selection = const_values[selection];

  static_assert(!std::is_same_v<decltype(mutable_selection), std::valarray<int>>);

  mutable_selection = 9;
  EXPECT_EQ(ToVector(mutable_values), (std::vector<int>{9, 2, 9, 4}));
  EXPECT_EQ(ToVector(copied_selection), (std::vector<int>{1, 3}));

  // mutable_selection 借用原数组；显式物化的 copied_selection 是独立值。const 子集
  // 的实现也可能先返回惰性表达式，因此需要独立快照时不要依赖 `auto`。代理不能比源
  // valarray 活得更久，源 resize、移动或销毁后也不能继续使用。
}

TEST(ValarraySubsets, MaterializeBeforeOverlappingRearrangement) {
  std::valarray<int> values{1, 2, 3, 4};
  const std::slice first_three{0, 3, 1};
  const std::slice last_three{1, 3, 1};
  const std::valarray<int> snapshot = std::as_const(values)[first_three];

  values[last_three] = snapshot;

  EXPECT_EQ(ToVector(values), (std::vector<int>{1, 1, 2, 3}));

  // 代理表达式可能引用原数组；当左右选择区域重叠时，先物化快照能明确“读取旧值，再
  // 写新值”的语义，避免依赖实现的求值和别名处理细节。
}

}  // namespace
