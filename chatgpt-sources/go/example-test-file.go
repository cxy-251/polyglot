package stdlib_test

import (
	"strings"
	"testing"
)

func TestStringsBuilder(t *testing.T) {
	var b strings.Builder
	b.WriteString("hello")
	b.WriteString(" world")

	if got := b.String(); got != "hello world" {
		t.Fatalf("builder string = %q", got)
	}
}
