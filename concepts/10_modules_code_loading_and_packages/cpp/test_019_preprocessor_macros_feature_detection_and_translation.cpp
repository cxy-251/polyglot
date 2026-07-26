// polyglot-covers:
// - cpp.language.object-function-and-variadic-macros
// - cpp.language.macro-parentheses-and-repeated-evaluation-traps
// - cpp.language.stringize-and-token-paste
// - cpp.language.va-opt
// - cpp.language.conditional-inclusion-and-has-include
// - cpp.language.predefined-macros-and-feature-tests
// - cpp.language.translation-phases

#include <gtest/gtest.h>

#include <string>
#include <vector>

#if !__has_include(<vector>)
#error "C++20 standard library must provide <vector>"
#endif

#define POLYGLOT_BAD_ADD(left, right) left + right
#define POLYGLOT_ADD(left, right) ((left) + (right))
#define POLYGLOT_MAX(left, right) ((left) > (right) ? (left) : (right))

#define POLYGLOT_STRINGIZE_RAW(token) #token
#define POLYGLOT_STRINGIZE(token) POLYGLOT_STRINGIZE_RAW(token)
#define POLYGLOT_JOIN_RAW(left, right) left##right
#define POLYGLOT_JOIN(left, right) POLYGLOT_JOIN_RAW(left, right)

#define POLYGLOT_VERSION_TOKEN 20
#define POLYGLOT_VECTOR(first, ...) \
  std::vector<int>{first __VA_OPT__(, ) __VA_ARGS__}

#define POLYGLOT_INCREMENT_BOTH(first, second) \
  do {                                            \
    ++(first);                                    \
    ++(second);                                   \
  } while (false)

namespace {

std::string current_function_name() { return __func__; }

TEST(Macros, EveryParameterAndWholeExpansionNeedParentheses) {
  int bad_result = 2 * POLYGLOT_BAD_ADD(3, 4);
  int good_result = 2 * POLYGLOT_ADD(3, 4);

  EXPECT_EQ(bad_result, 10);
  EXPECT_EQ(good_result, 14);

  // 预处理器只替换 token：坏宏展开成 2 * 3 + 4，完全不理解调用者期待的分组。
  // 即使正确加括号，宏仍没有类型、作用域和单次求值保证，普通逻辑优先用函数模板。
}

TEST(Macros, ReusingAParameterCanRepeatItsSideEffects) {
  int calls = 0;
  auto next = [&calls] {
    ++calls;
    return calls;
  };

  int selected = POLYGLOT_MAX(next(), 0);
  EXPECT_EQ(selected, 2);
  EXPECT_EQ(calls, 2);

  // 宏条件第一次求值 next()，选中左分支后又求值一次。这里两次有 sequencing，结果
  // 可预测；若把 i++ 同时放进无序算术操作，甚至可能产生未定义行为。
}

TEST(Macros, StringizeAndTokenPasteOperateBeforeCompilation) {
  EXPECT_STREQ(POLYGLOT_STRINGIZE(POLYGLOT_VERSION_TOKEN), "20");

  int joined_name = 7;
  EXPECT_EQ(POLYGLOT_JOIN(joined_, name), 7);

  // 两层宏让参数先展开再执行 # 或 ##；直接 stringize 参数只会得到宏名字文本。
  // token paste 必须产生合法预处理 token，它不是运行期字符串拼接。
}

TEST(Macros, VaOptAddsPunctuationOnlyWhenVariadicTokensExist) {
  auto one = POLYGLOT_VECTOR(1);
  auto many = POLYGLOT_VECTOR(1, 2, 3);

  EXPECT_EQ(one, (std::vector<int>{1}));
  EXPECT_EQ(many, (std::vector<int>{1, 2, 3}));

  // C++20 __VA_OPT__ 仅在可变参数非空时展开内容，这里条件性加入逗号，避免依赖
  // `, ##__VA_ARGS__` 等编译器扩展处理空参数列表。
}

TEST(Macros, DoWhileZeroMakesAMultiStatementMacroActAsOneStatement) {
  int first = 1;
  int second = 2;

  if (first < second)
    POLYGLOT_INCREMENT_BOTH(first, second);
  else
    FAIL() << "unexpected branch";

  EXPECT_EQ(first, 2);
  EXPECT_EQ(second, 3);

  // do { ... } while(false) 把多条语句包装成一个需要分号的 statement，避免 if/else
  // 绑定错误。它仍不如 inline 函数安全，只适合必须参与预处理的少数场景。
}

TEST(FeatureDetection, StandardAndImplementationExposeFeatureInformation) {
  EXPECT_GE(__cplusplus, 202002L);
  EXPECT_GT(__has_cpp_attribute(nodiscard), 0);
  EXPECT_GT(std::string{__FILE__}.size(), 0U);
  EXPECT_EQ(current_function_name(), "current_function_name");

  // __cplusplus 表示请求的语言模式；__has_include 和 __has_cpp_attribute 用于能力检测。
  // 应检测具体特性，而不是假设某个编译器版本一次实现了整套 C++20。
}

TEST(Translation, CommentsMacrosAndAdjacentStringsAreHandledInOrderedPhases) {
  std::string text = "tokens "
                     "become one literal";
  EXPECT_EQ(text, "tokens become one literal");

  // 源文件先经历字符映射、行拼接和 token 化，注释替换为空格，随后执行预处理指令；
  // 字符串字面量拼接发生在宏展开之后。理解阶段顺序有助于解释宏和转义的反直觉结果。
}

}  // namespace

#undef POLYGLOT_INCREMENT_BOTH
#undef POLYGLOT_VECTOR
#undef POLYGLOT_VERSION_TOKEN
#undef POLYGLOT_JOIN
#undef POLYGLOT_JOIN_RAW
#undef POLYGLOT_STRINGIZE
#undef POLYGLOT_STRINGIZE_RAW
#undef POLYGLOT_MAX
#undef POLYGLOT_ADD
#undef POLYGLOT_BAD_ADD
