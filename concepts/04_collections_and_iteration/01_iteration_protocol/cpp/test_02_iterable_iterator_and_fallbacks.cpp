// 可迭代对象、迭代器与协议 fallback。
// 共同问题：容器与单次游标如何区分；每次取得迭代器是否共享状态；
// 缺少主要协议入口时是否存在兼容 fallback。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/cpp/standard_library/08_iterators/
// polyglot-related+: test_071_iterator_traits_concepts_indirect_access_and_customization_points.cpp
// polyglot-related: languages/cpp/standard_library/08_iterators/
// polyglot-related+: test_077_stream_iterators_formatted_values_raw_characters_and_output_delimiters.cpp

#include <gtest/gtest.h>

#include <concepts>
#include <iterator>
#include <ranges>
#include <sstream>
#include <vector>

namespace {

TEST(IterableIteratorConcept, RangeAndIteratorAreSeparateProtocolRoles) {
  using Range = std::vector<int>;
  using Iterator = Range::iterator;

  static_assert(std::ranges::forward_range<Range>);
  static_assert(std::forward_iterator<Iterator>);
  static_assert(!std::ranges::range<Iterator>);
  static_assert(!std::input_iterator<Range>);

  Range values{1, 2};
  Iterator first = values.begin();
  Iterator second = values.begin();
  ++first;

  EXPECT_EQ(*first, 2);
  EXPECT_EQ(*second, 1);
}

TEST(IterableIteratorConcept, InputIteratorExpressesASinglePassSource) {
  std::istringstream input{"10 20"};
  using Iterator = std::istream_iterator<int>;

  static_assert(std::input_iterator<Iterator>);
  static_assert(!std::forward_iterator<Iterator>);

  Iterator iterator{input};
  const Iterator end;

  ASSERT_NE(iterator, end);
  EXPECT_EQ(*iterator, 10);
  ++iterator;
  ASSERT_NE(iterator, end);
  EXPECT_EQ(*iterator, 20);
  ++iterator;
  EXPECT_EQ(iterator, end);

  // C++ 根据 iterator category/concept 表达多遍或单遍；不存在从 operator[] 自动合成
  // begin/end 的语言 fallback，自定义 range 必须提供可被 ranges CPO 找到的入口。
}

}  // namespace
