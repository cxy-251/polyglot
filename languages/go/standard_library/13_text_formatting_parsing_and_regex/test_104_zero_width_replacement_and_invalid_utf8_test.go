// polyglot-covers: go.regexp.zero-width-replacement-invalid-utf8
package textprocessing_test

import (
	"regexp"
	"testing"
	"unicode/utf8"
)

func TestReplacementExpandsCapturesAndInvalidUTF8IsObservable(t *testing.T) {
	expression := regexp.MustCompile(`([a-z]+)=(\d+)`)
	if got := expression.ReplaceAllString("x=7", `${1}:[${2}]`); got != "x:[7]" {
		t.Fatalf("replacement 使用 $name 或 ${index} 展开捕获: %q", got)
	}
	broken := string([]byte{0xff, 'A'})
	if utf8.ValidString(broken) {
		t.Fatal("string 可保存任意 bytes；UTF-8 有效性必须显式检查")
	}
	if indexes := regexp.MustCompile(`^|$`).FindAllStringIndex("A", -1); len(indexes) != 2 {
		t.Fatalf("零宽匹配遵循 FindAll 的相邻空匹配规则: %v", indexes)
	}
}
