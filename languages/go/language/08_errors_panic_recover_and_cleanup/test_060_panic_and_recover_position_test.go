// polyglot-covers: go.panic.recover-and-deferred-unwinding
package errorscleanup_test

import (
	"slices"
	"testing"
)

func recoverPanic() (recovered any) {
	defer func() { recovered = recover() }()
	panic("boom")
}

func observePanicUnwind() (events []string, recovered any) {
	defer func() {
		events = append(events, "recover")
		recovered = recover()
	}()
	defer func() { events = append(events, "cleanup") }()
	panic("failed")
}

func TestRecoverWorksOnlyInDeferredFunctionDuringPanicking(t *testing.T) {
	if recover() != nil {
		t.Fatal("非 panic 展开期间直接调用 recover 返回 nil")
	}
	if recoverPanic() != "boom" {
		t.Fatal("deferred function 可停止当前 goroutine 的 panic 展开")
	}
}

func TestPanicRunsDefersBeforeRecoveryReturns(t *testing.T) {
	events, recovered := observePanicUnwind()
	if recovered != "failed" || !slices.Equal(events, []string{"cleanup", "recover"}) {
		t.Fatalf("panic 展开执行 defer，最近的 defer 最先运行: %v %v", events, recovered)
	}
}
