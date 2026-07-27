// polyglot-covers: go.cleanup.return-panic-defer
package errorscleanup_test

import (
	"slices"
	"testing"
)

func observePanicUnwind() (events []string, recovered any) {
	defer func() {
		events = append(events, "recover")
		recovered = recover()
	}()
	defer func() { events = append(events, "cleanup") }()
	panic("failed")
}

func TestPanicRunsDefersBeforeRecoveryReturns(t *testing.T) {
	events, recovered := observePanicUnwind()
	if recovered != "failed" || !slices.Equal(events, []string{"cleanup", "recover"}) {
		t.Fatalf("panic 展开执行 defer，最近的 defer 最先运行: %v %v", events, recovered)
	}
}
