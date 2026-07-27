// polyglot-covers: go.errors.wrapping-is-join
package errorscleanup_test

import (
	"errors"
	"fmt"
	"testing"
)

func TestJoinPreservesMultipleErrorIdentities(t *testing.T) {
	first := errors.New("first")
	second := errors.New("second")
	wrapped := fmt.Errorf("operation: %w", first)
	combined := errors.Join(wrapped, second)
	if !errors.Is(combined, first) || !errors.Is(combined, second) {
		t.Fatal("Join 形成多分支 unwrap 图，Is 可匹配任一组成错误")
	}
	if errors.Join(nil, nil) != nil {
		t.Fatal("全部输入为 nil 时 Join 返回 nil")
	}
}
