// polyglot-covers: go.generics.functions-types-and-inference
package generics_test

import "testing"

func firstValue[T any](values []T) T { return values[0] }

type stack[T any] struct {
	values []T
}

func (items *stack[T]) Push(value T) { items.values = append(items.values, value) }
func (items *stack[T]) Pop() T {
	index := len(items.values) - 1
	value := items.values[index]
	items.values = items.values[:index]
	return value
}

func TestTypeArgumentsCanBeInferredFromOrdinaryArguments(t *testing.T) {
	if firstValue([]int{3, 4}) != 3 || firstValue[string]([]string{"go"}) != "go" {
		t.Fatal("编译器通常从实参推断类型参数，也允许显式给出")
	}
}

func TestGenericTypeKeepsOneElementTypePerInstantiation(t *testing.T) {
	items := stack[string]{}
	items.Push("go")
	if items.Pop() != "go" {
		t.Fatal("generic type 的每个实例化拥有具体字段和方法类型")
	}
}
