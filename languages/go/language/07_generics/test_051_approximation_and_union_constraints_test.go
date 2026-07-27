// polyglot-covers: go.generics.approximation-and-unions
package generics_test

import "testing"

type distance int

type addable interface {
	~int | ~string
}

func addValues[T addable](left, right T) T { return left + right }

func TestTildeIncludesDefinedTypesWithMatchingUnderlyingType(t *testing.T) {
	if addValues(distance(2), distance(3)) != 5 || addValues("go", "pher") != "gopher" {
		t.Fatal("~int 包含底层类型为 int 的 defined type；union 合并允许的 type terms")
	}
}
