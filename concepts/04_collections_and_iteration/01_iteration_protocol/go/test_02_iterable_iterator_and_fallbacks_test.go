// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/go/language/07_generics/test_054_generic_method_boundaries_test.go
//
// 共同问题：用户类型如何参与迭代；是否区分 iterable 与 iterator；提前停止如何反馈给生产者。
// 对照观察：Go 没有隐式迭代方法 fallback；range-over-function 使用 iter.Seq 的 yield bool 协议。
package iteration_protocol

import (
	"iter"
	"slices"
	"testing"
)

func numbers(limit int) iter.Seq[int] {
	return func(yield func(int) bool) {
		for value := range limit {
			if !yield(value) {
				return
			}
		}
	}
}

func TestRangeOverFunctionReportsEarlyStop(t *testing.T) {
	visited := []int{}
	for value := range numbers(5) {
		visited = append(visited, value)
		if value == 2 {
			break
		}
	}
	if !slices.Equal(visited, []int{0, 1, 2}) {
		t.Fatalf("break 使隐式 yield 返回 false，生产者必须停止: %v", visited)
	}
}
