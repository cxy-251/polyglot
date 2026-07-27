// polyglot-covers: go.generics.functions-and-inference
package generics_test

import "testing"

func firstValue[T any](values []T) T { return values[0] }

func TestTypeArgumentsCanBeInferredFromOrdinaryArguments(t *testing.T) {
	if firstValue([]int{3, 4}) != 3 || firstValue[string]([]string{"go"}) != "go" {
		t.Fatal("编译器通常从实参推断类型参数，也允许显式给出")
	}
}
