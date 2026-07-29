// polyglot-covers: go.collections.slice-growth-copy-and-capacity
package collections_test

import (
	"slices"
	"testing"
)

func TestAppendMayReuseOrReplaceBackingStorage(t *testing.T) {
	base := make([]int, 1, 2)
	base[0] = 1
	shared := append(base, 2)
	shared[0] = 10
	if base[0] != 10 {
		t.Fatal("容量足够时 append 可复用 backing array")
	}
	detached := append(shared, 3)
	detached[0] = 99
	if shared[0] != 10 {
		t.Fatal("容量不足时 append 分配新数组；调用方必须接收返回的 slice")
	}
}

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
