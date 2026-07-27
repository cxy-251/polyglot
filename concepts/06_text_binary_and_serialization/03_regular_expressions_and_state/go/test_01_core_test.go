// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_103_regexp_syntax_captures_and_re2_boundaries_test.go
//
// 共同问题：匹配结果如何暴露捕获；重复调用是否携带可变游标；表达式能否并发复用。
// 对照观察：Go Regexp 的 Find 方法不保存 lastIndex；编译后值除配置方法外可由 goroutine 并发使用。
package regular_expressions_and_state

import (
	"regexp"
	"slices"
	"testing"
)

func TestFindAllReturnsExplicitMatchesWithoutHiddenCursor(t *testing.T) {
	expression := regexp.MustCompile(`(?P<word>[a-z]+)=(\d+)`)
	first := expression.FindStringSubmatch("a=1")
	second := expression.FindStringSubmatch("b=2")
	if first[expression.SubexpIndex("word")] != "a" || second[1] != "b" {
		t.Fatal("每次调用从给定输入开始，不依赖上次匹配状态")
	}
	if !slices.Equal(expression.FindAllString("a=1 b=2", -1), []string{"a=1", "b=2"}) {
		t.Fatal("FindAll 显式返回全部非重叠匹配")
	}
}
