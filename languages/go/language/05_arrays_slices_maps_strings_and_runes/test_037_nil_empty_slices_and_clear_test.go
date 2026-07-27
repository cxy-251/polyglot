// polyglot-covers: go.collections.nil-empty-slice-clear
package collections_test

import "testing"

func TestNilAndEmptySlicesShareLengthButNotNilState(t *testing.T) {
	var absent []int
	empty := []int{}
	if len(absent) != 0 || len(empty) != 0 || absent != nil || empty == nil {
		t.Fatal("nil slice 与非 nil empty slice 的长度都为零，但 nil 状态不同")
	}
	values := []int{1, 2}
	clear(values)
	if values[0] != 0 || len(values) != 2 {
		t.Fatal("clear 将元素设为零值，不改变 slice 长度")
	}
}
