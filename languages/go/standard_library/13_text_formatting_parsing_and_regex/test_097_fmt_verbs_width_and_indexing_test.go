// polyglot-covers: go.fmt.verbs-and-formatting-interfaces
package textprocessing_test

import (
	"fmt"
	"testing"
)

type point struct{ x, y int }

func (value point) String() string { return fmt.Sprintf("(%d,%d)", value.x, value.y) }

type masked string

func (value masked) Format(state fmt.State, verb rune) {
	if _, err := fmt.Fprintf(state, "<%c:%d>", verb, len(value)); err != nil {
		panic(err)
	}
}

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

func TestFormattingInterfacesOverrideDefaultPresentation(t *testing.T) {
	if fmt.Sprint(point{2, 3}) != "(2,3)" || fmt.Sprintf("%v", masked("secret")) != "<v:6>" {
		t.Fatal("Stringer 提供普通文本；Formatter 接收 verb 并自定义输出")
	}
}
