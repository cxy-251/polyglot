// polyglot-covers: go.fmt.verbs-width-indexing
package textprocessing_test

import (
	"fmt"
	"testing"
)

func TestFormattingVerbsCarryTypeAndLayoutIntent(t *testing.T) {
	got := fmt.Sprintf("%[2]s:%[1]d:%#[1]x", 15, "id")
	padded := fmt.Sprintf("%04d", 15)
	if got != "id:15:0xf" || padded != "0015" {
		t.Fatalf("显式 argument index 可复用值，宽度和 flag 决定布局: %q %q", got, padded)
	}
	if fmt.Sprintf("%T", got) != "string" {
		t.Fatal("类型格式化 verb 输出动态类型")
	}
}
