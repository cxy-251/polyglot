// polyglot-family: text_binary_and_serialization
// polyglot-concept: unicode_strings_and_code_units
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_040_utf8_strings_bytes_and_runes_test.go
//
// 共同问题：字符串长度和索引单位是什么；如何遍历 code point；grapheme 是否等同字符。
// 对照观察：Go string 是只读 bytes，range 解码 rune；标准库不提供 grapheme cluster 索引。
package unicode_strings_and_code_units

import (
	"testing"
	"unicode/utf8"
)

func TestBytesRunesAndUserPerceivedCharactersDiffer(t *testing.T) {
	text := "A界"
	runes := []rune(text)
	if len(text) != 4 || len(runes) != 2 || utf8.RuneCountInString(text) != 2 {
		t.Fatal("len(string) 计 bytes；[]rune 与 RuneCount 计解码后的 code points")
	}
	emoji := "👩‍💻"
	if utf8.RuneCountInString(emoji) != 3 {
		t.Fatal("一个用户感知 grapheme 可由多个 rune 组成")
	}
}
