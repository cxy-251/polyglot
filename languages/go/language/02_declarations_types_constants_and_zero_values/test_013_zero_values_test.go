// polyglot-covers: go.types.zero-values
package declarations_test

import "testing"

type zeroRecord struct {
	count int
	ready bool
	name  string
}

func TestDeclaredStorageStartsAtRecursiveZeroValue(t *testing.T) {
	var record zeroRecord
	var numbers [2]int
	if record != (zeroRecord{}) || numbers != [2]int{0, 0} {
		t.Fatal("struct 与 array 的零值由字段和元素零值递归组成")
	}
	var pointer *zeroRecord
	if pointer != nil {
		t.Fatal("pointer 的零值是 nil")
	}
}
