// polyglot-covers: go.cleanup.failure-and-original-error
package errorscleanup_test

import (
	"errors"
	"testing"
)

var errOperation = errors.New("operation failed")
var errCleanup = errors.New("cleanup failed")

func operationWithCleanupFailure() (err error) {
	defer func() { err = errors.Join(err, errCleanup) }()
	return errOperation
}

func TestCleanupMustExplicitlyPreserveOriginalError(t *testing.T) {
	err := operationWithCleanupFailure()
	if !errors.Is(err, errOperation) || !errors.Is(err, errCleanup) {
		t.Fatal("defer 没有自动异常聚合协议；实现必须显式 Join 或选择覆盖策略")
	}
}
