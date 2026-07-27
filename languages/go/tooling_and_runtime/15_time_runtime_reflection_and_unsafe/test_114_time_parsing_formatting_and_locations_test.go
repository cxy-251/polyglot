// polyglot-covers: go.time.parsing-formatting-locations
package runtimeintrospection_test

import (
	"testing"
	"time"
)

func TestLayoutsUseReferenceTimeAndLocationIsExplicit(t *testing.T) {
	const layout = "2006-01-02 15:04 MST"
	value, err := time.Parse(layout, "2026-07-27 08:30 UTC")
	if err != nil {
		t.Fatal(err)
	}
	if value.Location() != time.UTC || value.Format(time.RFC3339) != "2026-07-27T08:30:00Z" {
		t.Fatalf("layout 用固定参考时间描述字段；Parse 结果携带 location: %v", value)
	}
}
