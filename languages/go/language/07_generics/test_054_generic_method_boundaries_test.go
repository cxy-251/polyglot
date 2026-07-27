// polyglot-covers: go.generics.method-boundaries
package generics_test

import "testing"

type pairBox[T any] struct {
	left  T
	right T
}

func (pair pairBox[T]) Values() (T, T) { return pair.left, pair.right }

func TestMethodReusesReceiverTypeParameters(t *testing.T) {
	left, right := (pairBox[int]{left: 1, right: 2}).Values()
	if left != 1 || right != 2 {
		t.Fatal("generic receiver 的方法可复用接收者类型参数")
	}
	// 方法不能声明额外的独立类型参数；需要新参数时使用 generic function。
}
