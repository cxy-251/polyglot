// polyglot-covers: go.collections.copy-full-slice-overlap
package collections_test

import (
	"slices"
	"testing"
)

func TestCopySupportsOverlapAndFullSliceLimitsGrowth(t *testing.T) {
	values := []int{1, 2, 3, 4}
	copy(values[1:], values[:3])
	if !slices.Equal(values, []int{1, 1, 2, 3}) {
		t.Fatalf("内建 copy 对重叠区域有确定语义: %v", values)
	}
	window := values[:2:2]
	grown := append(window, 9)
	grown[0] = 7
	if values[0] != 1 {
		t.Fatal("full slice expression 将 capacity 限为 2，后续 append 必须分配")
	}
}
