// polyglot-covers:
// - cpp.stdlib.utility.pair-construction-and-conversion
// - cpp.stdlib.utility.make-pair-and-reference-wrapper-unwrapping
// - cpp.stdlib.utility.piecewise-construct
// - cpp.stdlib.utility.pair-access-comparison-and-swap
// - cpp.stdlib.utility.tuple-construction-and-access
// - cpp.stdlib.utility.make-tuple-tie-ignore-and-forward-as-tuple
// - cpp.stdlib.utility.tuple-cat
// - cpp.stdlib.utility.tuple-size-and-tuple-element
// - cpp.stdlib.utility.apply-and-make-from-tuple

#include <gtest/gtest.h>

#include <compare>
#include <functional>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>

namespace {

class ExplicitInteger {
 public:
  explicit ExplicitInteger(int value) : value_(value) {}
  int value() const { return value_; }

 private:
  int value_;
};

class Endpoint {
 public:
  Endpoint(std::string host, int port)
      : host_(std::move(host)), port_(port) {}

  Endpoint(const Endpoint&) = delete;
  Endpoint& operator=(const Endpoint&) = delete;
  Endpoint(Endpoint&&) noexcept = default;
  Endpoint& operator=(Endpoint&&) noexcept = default;

  const std::string& host() const { return host_; }
  int port() const { return port_; }

 private:
  std::string host_;
  int port_;
};

struct Rectangle {
  Rectangle(int width, int height) : width(width), height(height) {}
  int area() const { return width * height; }

  int width;
  int height;
};

TEST(Pair, ConstructionConversionAndMembersRetainTwoDifferentTypes) {
  std::pair<int, std::string> entry{7, "seven"};
  std::pair<long, std::string> widened = entry;

  EXPECT_EQ(entry.first, 7);
  EXPECT_EQ(entry.second, "seven");
  EXPECT_EQ(widened.first, 7L);
  static_assert(
      std::is_same_v<decltype(entry)::first_type, int>);
  static_assert(
      std::is_same_v<decltype(entry)::second_type, std::string>);

  using ExplicitPair = std::pair<ExplicitInteger, std::string>;
  static_assert(std::is_constructible_v<ExplicitPair, int, const char*>);
  static_assert(!std::is_convertible_v<std::pair<int, const char*>, ExplicitPair>);

  // pair 的转换构造会分别检查 first 和 second；只要任一元素的转换
  // 是 explicit，整个 pair 转换也不能隐式发生。这与“两个元素都能构造”是不同问题。
}

TEST(Pair, MakePairDecaysValuesButUnwrapsReferenceWrapper) {
  int counter = 3;
  auto pair = std::make_pair(std::ref(counter), std::string{"jobs"});

  static_assert(std::is_same_v<decltype(pair), std::pair<int&, std::string>>);
  pair.first += 2;

  EXPECT_EQ(counter, 5);
  EXPECT_EQ(pair.second, "jobs");

  // make_pair 通常对实参做 decay，避免意外保存局部引用；std::ref 是显式的
  // 例外，reference_wrapper<T> 会被 unwrap 为 T&。因此这个 pair 修改的是原 counter。
}

TEST(Pair, PiecewiseConstructPassesASeparateArgumentTupleToEachElement) {
  std::pair<Endpoint, Endpoint> connection{
      std::piecewise_construct,
      std::forward_as_tuple("client.local", 8080),
      std::forward_as_tuple("server.local", 443),
  };

  EXPECT_EQ(connection.first.host(), "client.local");
  EXPECT_EQ(connection.first.port(), 8080);
  EXPECT_EQ(connection.second.host(), "server.local");
  EXPECT_EQ(connection.second.port(), 443);

  // 普通 pair 构造每个元素只接收一个实参；piecewise_construct 把后两个 tuple
  // 分别展开成 first 和 second 的构造参数，可原地构造不可复制的多参数对象。
}

TEST(Pair, GetSupportsIndexesAndUniqueTypesWhileComparisonIsLexicographic) {
  std::pair<int, std::string> left{1, "z"};
  std::pair<int, std::string> right{2, "a"};

  EXPECT_EQ(std::get<0>(left), 1);
  EXPECT_EQ(std::get<std::string>(left), "z");
  EXPECT_LT(left, right);
  static_assert(
      std::is_same_v<decltype(left <=> right), std::strong_ordering>);

  std::swap(left, right);
  EXPECT_EQ(left.first, 2);
  EXPECT_EQ(right.first, 1);

  // pair 比较先看 first，只在等价时再看 second，不是同时比两个字段。
  // get<T> 只在 T 恰好出现一次时可用；pair<int, int> 必须用 get<0/1> 消除歧义。
}

TEST(Tuple, ConstructionAccessAndTraitsDescribeAHeterogeneousProduct) {
  std::tuple<int, std::string, double> row{4, "score", 9.5};

  EXPECT_EQ(std::get<0>(row), 4);
  EXPECT_EQ(std::get<std::string>(row), "score");
  EXPECT_DOUBLE_EQ(std::get<2>(row), 9.5);
  static_assert(std::tuple_size_v<decltype(row)> == 3);
  static_assert(
      std::is_same_v<std::tuple_element_t<1, decltype(row)>, std::string>);

  // tuple_size 和 tuple_element 在编译期描述元素数量与类型，get 才访问对象。
  // get<T> 同样要求类型唯一；重复类型的 tuple 应使用索引作为稳定位置协议。
}

TEST(Tuple, MakeTupleTieAndIgnoreControlOwnershipAndAssignment) {
  int id = 0;
  std::string name;
  double ignored_score = 0.0;

  auto owned = std::make_tuple(7, std::string{"Ada"}, 9.8);
  std::tie(id, name, std::ignore) = owned;

  EXPECT_EQ(id, 7);
  EXPECT_EQ(name, "Ada");
  EXPECT_DOUBLE_EQ(ignored_score, 0.0);
  static_assert(
      std::is_same_v<decltype(std::tie(id, name)), std::tuple<int&, std::string&>>);

  // make_tuple 像 make_pair 一样持有 decay 后的值，tie 则专门创建 lvalue reference
  // tuple，常用于拆分返回值。ignore 是可赋值占位符，不会改变任何业务变量。
}

TEST(Tuple, ForwardAsTupleIsSafeForImmediateForwardingButMustNotBeStored) {
  const auto consume = [](auto&& arguments) {
    return std::apply(
        [](std::string text, int repeat) {
          std::string result;
          while (repeat-- > 0) {
            result += text;
          }
          return result;
        },
        std::forward<decltype(arguments)>(arguments));
  };

  EXPECT_EQ(
      consume(std::forward_as_tuple(std::string{"go"}, 3)),
      "gogogo");

  // forward_as_tuple 保存 T&&/T& 而不拥有对象。这里在同一 full-expression
  // 内立即消费，临时 string 仍存活；若把返回的 tuple 存起来下一句再用，其中引用就会悬空。
}

TEST(Tuple, TupleCatComposesTupleLikeObjectsAndPreservesExplicitReferences) {
  int id = 5;
  auto reference = std::tie(id);
  std::pair<std::string, double> details{"load", 0.75};

  auto combined = std::tuple_cat(reference, details, std::tuple{true});
  static_assert(
      std::is_same_v<
          decltype(combined),
          std::tuple<int&, std::string, double, bool>>);

  std::get<0>(combined) = 8;
  EXPECT_EQ(id, 8);
  EXPECT_EQ(std::get<1>(combined), "load");
  EXPECT_TRUE(std::get<3>(combined));

  // tuple_cat 接受 tuple、pair 等 tuple-like 对象并按顺序连接。tie 明确带入的
  // int& 被保留，而普通 pair 的元素在结果中仍是独立值；需根据寿命决定是否要引用。
}

TEST(Tuple, ApplyAndMakeFromTupleBridgeProductValuesAndCallables) {
  const auto dimensions = std::tuple{6, 7};
  const Rectangle rectangle = std::make_from_tuple<Rectangle>(dimensions);
  const int multiplied = std::apply(std::multiplies<>{}, dimensions);

  EXPECT_EQ(rectangle.area(), 42);
  EXPECT_EQ(multiplied, 42);

  // apply 把 tuple-like 元素展开为 INVOKE 实参，make_from_tuple 把同一个展开用于
  // 目标类型构造。元素的 cv/ref 传递取决于 tuple 实参的值类别，不是一律复制。
}

}  // namespace
