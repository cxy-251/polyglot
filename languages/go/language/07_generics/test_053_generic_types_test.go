// polyglot-covers: go.generics.generic-types
package generics_test

import "testing"

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

func TestGenericTypeKeepsOneElementTypePerInstantiation(t *testing.T) {
	items := stack[string]{}
	items.Push("go")
	if items.Pop() != "go" {
		t.Fatal("generic type 的每个实例化拥有具体字段和方法类型")
	}
}
