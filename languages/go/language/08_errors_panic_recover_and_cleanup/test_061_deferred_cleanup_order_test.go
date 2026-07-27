// polyglot-covers: go.cleanup.defer-lifo
package errorscleanup_test

import (
	"slices"
	"testing"
)

func cleanupOrder() (events []string) {
	defer func() { events = append(events, "first") }()
	defer func() { events = append(events, "second") }()
	return
}

func TestDeferredCleanupsRunInReverseRegistrationOrder(t *testing.T) {
	if events := cleanupOrder(); !slices.Equal(events, []string{"second", "first"}) {
		t.Fatalf("多个资源通常在成功取得后立即 defer，最终按 LIFO 清理: %v", events)
	}
}
