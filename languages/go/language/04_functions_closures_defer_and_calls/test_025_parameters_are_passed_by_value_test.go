// polyglot-covers: go.functions.value-and-variadic-parameters
package functions_test

import "testing"

func replaceNumber(value int) { value = 99 }
func replaceThroughPointer(value *int) {
	*value = 99
}

func sum(prefix int, values ...int) int {
	total := prefix
	for _, value := range values {
		total += value
	}
	return total
}

func TestParameterVariablesReceiveCopies(t *testing.T) {
	number := 1
	replaceNumber(number)
	if number != 1 {
		t.Fatal("普通参数复制值，重绑形参不影响调用方")
	}
	replaceThroughPointer(&number)
	if number != 99 {
		t.Fatal("指针本身也按值复制，但复制的指针仍指向同一存储")
	}
}

func TestVariadicParameterIsASliceInsideTheFunction(t *testing.T) {
	values := []int{2, 3}
	if sum(1, values...) != 6 || sum(1) != 1 {
		t.Fatal("slice 通过 ... 展开；省略可变参数得到非 nil/empty 细节不应成为 API 契约")
	}
}
