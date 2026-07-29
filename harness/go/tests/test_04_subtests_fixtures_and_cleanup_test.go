// polyglot-harness: go.subtests_fixtures_and_cleanup
package goharness_test

import (
	"os"
	"path/filepath"
	"slices"
	"testing"
)

func TestSubtestOwnsTemporaryStateAndCleanup(t *testing.T) {
	events := []string{}
	t.Run("isolated fixture", func(t *testing.T) {
		t.Setenv("POLYGLOT_GO_FIXTURE", "active")
		path := filepath.Join(t.TempDir(), "value.txt")
		if err := os.WriteFile(path, []byte("ok"), 0o600); err != nil {
			t.Fatal(err)
		}
		t.Cleanup(func() { events = append(events, "cleanup") })
		events = append(events, os.Getenv("POLYGLOT_GO_FIXTURE"))
	})
	if !slices.Equal(events, []string{"active", "cleanup"}) {
		t.Fatalf("subtest 返回前应执行自己的 cleanup: %v", events)
	}
}
