// polyglot-covers: go.unicode.categories-normalization-boundary
package textprocessing_test

import (
	"testing"
	"unicode"
	"unicode/utf8"
)

func TestUnicodeCategoriesDoNotImplyNormalization(t *testing.T) {
	if !unicode.IsLetter('界') || !unicode.IsDigit('７') {
		t.Fatal("unicode tables 按 code point 属性分类")
	}
	composed := "é"
	decomposed := "e\u0301"
	if composed == decomposed || utf8.RuneCountInString(composed) == utf8.RuneCountInString(decomposed) {
		t.Fatal("规范等价序列仍是不同 byte/rune 序列")
	}
	// 标准库不提供 Unicode normalization；需要时应显式选择并锁定外部实现。
}
