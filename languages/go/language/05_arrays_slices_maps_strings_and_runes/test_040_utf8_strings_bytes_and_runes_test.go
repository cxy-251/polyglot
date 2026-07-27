// polyglot-covers: go.text.utf8-string-byte-rune-range
package collections_test

import (
	"testing"
	"unicode/utf8"
)

func TestStringLengthCountsBytesWhileRangeDecodesRunes(t *testing.T) {
	text := "A界"
	if len(text) != 4 || utf8.RuneCountInString(text) != 2 {
		t.Fatal("string 是只读 byte 序列；len 不是 Unicode code point 数")
	}
	indexes := []int{}
	runes := []rune{}
	for index, value := range text {
		indexes = append(indexes, index)
		runes = append(runes, value)
	}
	if indexes[1] != 1 || runes[1] != '界' || string([]byte(text)) != text {
		t.Fatal("range 返回 UTF-8 起始 byte index 与解码后的 rune")
	}
}
