// polyglot-covers: go.fmt.stringer-and-formatter
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

func TestFormattingInterfacesOverrideDefaultPresentation(t *testing.T) {
	if fmt.Sprint(point{2, 3}) != "(2,3)" || fmt.Sprintf("%v", masked("secret")) != "<v:6>" {
		t.Fatal("Stringer 提供普通文本；Formatter 接收 verb 并自定义输出")
	}
}
