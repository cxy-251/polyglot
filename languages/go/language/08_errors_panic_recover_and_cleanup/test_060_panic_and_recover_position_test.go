// polyglot-covers: go.panic.recover-position
package errorscleanup_test

import "testing"

func recoverPanic() (recovered any) {
	defer func() { recovered = recover() }()
	panic("boom")
}

func TestRecoverWorksOnlyInDeferredFunctionDuringPanicking(t *testing.T) {
	if recover() != nil {
		t.Fatal("非 panic 展开期间直接调用 recover 返回 nil")
	}
	if recoverPanic() != "boom" {
		t.Fatal("deferred function 可停止当前 goroutine 的 panic 展开")
	}
}
