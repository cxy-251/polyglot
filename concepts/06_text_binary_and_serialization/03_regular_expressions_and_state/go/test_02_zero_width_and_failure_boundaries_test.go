// polyglot-family: text_binary_and_serialization
// polyglot-concept: regular_expressions_and_state
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_104_zero_width_replacement_and_invalid_utf8_test.go
//
// 共同问题：零宽匹配如何推进；无效模式何时失败；高级回溯特性是否存在。
// 对照观察：Compile 返回语法 error，MustCompile panic；RE2 保证线性时间并拒绝 backreference。
package regular_expressions_and_state

import (
	"regexp"
	"testing"
)

func TestZeroWidthAndUnsupportedSyntaxHaveDefinedBoundaries(t *testing.T) {
	indexes := regexp.MustCompile(`^|$`).FindAllStringIndex("A", -1)
	if len(indexes) != 2 || indexes[0][0] != 0 || indexes[1][0] != 1 {
		t.Fatalf("FindAll 忽略与前一匹配相邻的重复空匹配并继续推进: %v", indexes)
	}
	if _, err := regexp.Compile(`(a)\1`); err == nil {
		t.Fatal("backreference 不属于 Go RE2 syntax")
	}
}
