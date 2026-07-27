// polyglot-covers: go.collections.slice-header-length-capacity
package collections_test

import "testing"

func TestSliceCopySharesBackingArray(t *testing.T) {
	backing := [4]int{1, 2, 3, 4}
	view := backing[1:3]
	copyOfHeader := view
	copyOfHeader[0] = 20
	if backing[1] != 20 || len(view) != 2 || cap(view) != 3 {
		t.Fatal("slice 值复制的是指针、长度和容量组成的描述符，不复制底层元素")
	}
}
