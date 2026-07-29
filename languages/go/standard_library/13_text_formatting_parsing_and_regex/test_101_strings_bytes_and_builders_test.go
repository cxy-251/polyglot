// polyglot-covers: go.text.bytes-builders-unicode-and-normalization-boundary
package textprocessing_test

import (
	"bytes"
	"strings"
	"testing"
	"unicode"
	"unicode/utf8"
)

func TestStringAndByteHelpersUseDifferentMutationModels(t *testing.T) {
	if strings.TrimSpace(" go \n") != "go" {
		t.Fatal("strings 操作不可变 UTF-8 文本值并返回新 string")
	}
	buffer := bytes.NewBufferString("go")
	buffer.WriteByte('!')
	if buffer.String() != "go!" {
		t.Fatal("bytes.Buffer 维护可增长 byte 序列")
	}
	var builder strings.Builder
	builder.WriteString("course")
	if builder.String() != "course" {
		t.Fatal("strings.Builder 为只追加 string 构建优化，非零值复制后不可继续使用")
	}
}

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
