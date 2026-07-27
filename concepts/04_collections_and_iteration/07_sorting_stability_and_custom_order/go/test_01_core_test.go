// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_039_map_iteration_order_test.go
//
// 共同问题：排序是否稳定、是否原地修改；自定义顺序如何比较相等键。
// 对照观察：slices.SortStableFunc 原地排序并保留 comparator 返回 0 的相对顺序。
package sorting_stability_and_custom_order

import (
	"cmp"
	"slices"
	"testing"
)

type rankedItem struct {
	rank int
	name string
}

func TestStableComparatorPreservesEqualKeyOrder(t *testing.T) {
	values := []rankedItem{{2, "late"}, {1, "first"}, {1, "second"}}
	slices.SortStableFunc(values, func(left, right rankedItem) int {
		return cmp.Compare(left.rank, right.rank)
	})
	if values[0].name != "first" || values[1].name != "second" || values[2].name != "late" {
		t.Fatalf("稳定排序保持相等 rank 的原顺序: %v", values)
	}
}
