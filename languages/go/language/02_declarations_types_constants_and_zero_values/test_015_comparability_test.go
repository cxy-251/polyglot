// polyglot-covers: go.types.comparability
package declarations_test

import "testing"

type comparableRecord struct {
	code int
	name string
}

func TestComparabilityDependsOnTheCompleteType(t *testing.T) {
	left := comparableRecord{code: 1, name: "go"}
	right := comparableRecord{code: 1, name: "go"}
	if left != right || [2]int{1, 2} != [2]int{1, 2} {
		t.Fatal("array 和全部字段可比较的 struct 支持值比较")
	}
	values := []int{1}
	if values == nil {
		t.Fatal("slice 只能与 nil 比较，不能与另一个 slice 比较")
	}
	// map、slice、function 不可作为普通比较操作数；map key 也必须是 comparable。
}
