// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/go/standard_library/13_text_formatting_parsing_and_regex/
// polyglot-related+: test_101_strings_bytes_and_builders_test.go
//
// 共同问题：规范等价字符串是否自动相等；无效编码怎样检测与迭代。
// 对照观察：Go 不自动 normalization；string 可保存无效 UTF-8，range 将坏序列解码为 RuneError。
package unicode_strings_and_code_units

import (
	"testing"
	"unicode/utf8"
)

func TestNormalizationAndValidityAreExplicitPolicies(t *testing.T) {
	if "é" == "e\u0301" {
		t.Fatal("规范等价的不同 byte 序列不会自动相等")
	}
	broken := string([]byte{0xff, 'A'})
	if utf8.ValidString(broken) {
		t.Fatal("无效 UTF-8 仍可存入 string")
	}
	first, size := utf8.DecodeRuneInString(broken)
	if first != utf8.RuneError || size != 1 {
		t.Fatalf("坏起始 byte 解码为宽度 1 的 RuneError: %U %d", first, size)
	}
}
