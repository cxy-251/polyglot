// polyglot-covers: go.generics.method-and-algorithm-boundaries
package generics_test

import (
	"slices"
	"testing"
)

type pairBox[T any] struct {
	left  T
	right T
}

func (pair pairBox[T]) Values() (T, T) { return pair.left, pair.right }

func mapSlice[S ~[]E, E any, R any](source S, transform func(E) R) []R {
	result := make([]R, 0, len(source))
	for _, value := range source {
		result = append(result, transform(value))
	}
	return result
}

func TestMethodReusesReceiverTypeParameters(t *testing.T) {
	left, right := (pairBox[int]{left: 1, right: 2}).Values()
	if left != 1 || right != 2 {
		t.Fatal("generic receiver 的方法可复用接收者类型参数")
	}
	// 方法不能声明额外的独立类型参数；需要新参数时使用 generic function。
}

func TestGenericAlgorithmPreservesNamedSliceInputs(t *testing.T) {
	type scores []int
	got := mapSlice(scores{1, 2}, func(value int) string { return string(rune('0' + value)) })
	if !slices.Equal(got, []string{"1", "2"}) {
		t.Fatalf("~[]E 允许 named slice，同时独立推断结果类型: %v", got)
	}
}
