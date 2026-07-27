// polyglot-covers: go.functions.variadic-and-slice-expansion
package functions_test

import "testing"

func sum(prefix int, values ...int) int {
	total := prefix
	for _, value := range values {
		total += value
	}
	return total
}

func TestVariadicParameterIsASliceInsideTheFunction(t *testing.T) {
	values := []int{2, 3}
	if sum(1, values...) != 6 || sum(1) != 1 {
		t.Fatal("slice 通过 ... 展开；省略可变参数得到非 nil/empty 细节不应成为 API 契约")
	}
}
