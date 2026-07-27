// polyglot-covers: go.cleanup.partial-acquisition
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

func TestOnlySuccessfullyAcquiredResourcesAreDeferred(t *testing.T) {
	events, err := acquireUntilFailure()
	if err == nil || !slices.Equal(events, []string{"acquire:first", "release:first"}) {
		t.Fatalf("defer 应紧随成功 acquisition，避免释放未取得资源: %v %v", events, err)
	}
}
