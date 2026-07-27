// polyglot-covers: go.regexp.syntax-captures-re2-boundary
package textprocessing_test

import (
	"regexp"
	"testing"
)

func TestRegexpCapturesAreIndexedAndNamed(t *testing.T) {
	expression := regexp.MustCompile(`(?P<key>[a-z]+)=(\d+)`)
	match := expression.FindStringSubmatch("count=42")
	if match[expression.SubexpIndex("key")] != "count" || match[2] != "42" {
		t.Fatalf("SubexpIndex 将名称映射到捕获位置: %v", match)
	}
	if _, err := regexp.Compile(`(a)\1`); err == nil {
		t.Fatal("Go regexp 使用 RE2 语义，不支持 backreference")
	}
}
