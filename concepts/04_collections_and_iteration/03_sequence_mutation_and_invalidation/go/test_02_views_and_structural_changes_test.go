// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_036_copy_full_slice_and_overlap_test.go
//
// 共同问题：受限 view 能否改变共享结构；原地算法如何影响其他别名。
// 对照观察：full slice expression 可限制 capacity 并强制增长分离；元素修改仍写入共享数组。
package sequence_mutation_and_invalidation

import (
	"slices"
	"testing"
)

func TestFullSliceExpressionControlsStructuralSharing(t *testing.T) {
	values := []int{3, 1, 2}
	view := values[:2:2]
	slices.Sort(view)
	if !slices.Equal(values, []int{1, 3, 2}) {
		t.Fatalf("原地 sort 通过 view 修改共享元素: %v", values)
	}
	extended := append(view, 9)
	extended[0] = 7
	if values[0] != 1 {
		t.Fatal("capacity 被限制后 append 分配，后续修改不再回写原数组")
	}
}
