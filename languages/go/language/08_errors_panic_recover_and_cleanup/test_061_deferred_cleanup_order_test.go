// polyglot-covers: go.cleanup.defer-order-and-partial-acquisition
package errorscleanup_test

import (
	"errors"
	"slices"
	"testing"
)

func acquireUntilFailure() (events []string, err error) {
	events = append(events, "acquire:first")
	defer func() { events = append(events, "release:first") }()
	err = errors.New("second acquisition failed")
	return
}

func cleanupOrder() (events []string) {
	defer func() { events = append(events, "first") }()
	defer func() { events = append(events, "second") }()
	return
}

func TestOnlySuccessfullyAcquiredResourcesAreDeferred(t *testing.T) {
	events, err := acquireUntilFailure()
	if err == nil || !slices.Equal(events, []string{"acquire:first", "release:first"}) {
		t.Fatalf("defer 应紧随成功 acquisition，避免释放未取得资源: %v %v", events, err)
	}
}

func TestDeferredCleanupsRunInReverseRegistrationOrder(t *testing.T) {
	if events := cleanupOrder(); !slices.Equal(events, []string{"second", "first"}) {
		t.Fatalf("多个资源通常在成功取得后立即 defer，最终按 LIFO 清理: %v", events)
	}
}
