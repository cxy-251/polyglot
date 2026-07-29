// polyglot-covers: go.errors.wrapping-joining-and-cleanup-failures
package errorscleanup_test

import (
	"errors"
	"fmt"
	"testing"
)

var errOperation = errors.New("operation failed")
var errCleanup = errors.New("cleanup failed")

func operationWithCleanupFailure() (err error) {
	defer func() { err = errors.Join(err, errCleanup) }()
	return errOperation
}

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

func TestCleanupMustExplicitlyPreserveOriginalError(t *testing.T) {
	err := operationWithCleanupFailure()
	if !errors.Is(err, errOperation) || !errors.Is(err, errCleanup) {
		t.Fatal("defer 没有自动异常聚合协议；实现必须显式 Join 或选择覆盖策略")
	}
}
