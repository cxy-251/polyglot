// polyglot-covers: go.collections.arrays-and-slice-views
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

func TestSliceCopySharesBackingArray(t *testing.T) {
	backing := [4]int{1, 2, 3, 4}
	view := backing[1:3]
	copyOfHeader := view
	copyOfHeader[0] = 20
	if backing[1] != 20 || len(view) != 2 || cap(view) != 3 {
		t.Fatal("slice 值复制的是指针、长度和容量组成的描述符，不复制底层元素")
	}
}
