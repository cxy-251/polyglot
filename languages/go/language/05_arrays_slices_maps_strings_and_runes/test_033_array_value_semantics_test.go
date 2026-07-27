// polyglot-covers: go.collections.array-value-semantics
package collections_test

import "testing"

func TestArrayAssignmentCopiesEveryElement(t *testing.T) {
	original := [3]int{1, 2, 3}
	copied := original
	copied[0] = 99
	if original[0] != 1 || copied[0] != 99 {
		t.Fatal("array 是值；赋值和传参复制完整数组")
	}
	// 长度属于 array 类型，因此 [2]int 与 [3]int 是不同类型，不能直接赋值。
}
