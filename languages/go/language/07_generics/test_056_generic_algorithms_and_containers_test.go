// polyglot-covers: go.generics.algorithms-and-containers
package generics_test

import (
	"slices"
	"testing"
)

func mapSlice[S ~[]E, E any, R any](source S, transform func(E) R) []R {
	result := make([]R, 0, len(source))
	for _, value := range source {
		result = append(result, transform(value))
	}
	return result
}

func TestGenericAlgorithmPreservesNamedSliceInputs(t *testing.T) {
	type scores []int
	got := mapSlice(scores{1, 2}, func(value int) string { return string(rune('0' + value)) })
	if !slices.Equal(got, []string{"1", "2"}) {
		t.Fatalf("~[]E 允许 named slice，同时独立推断结果类型: %v", got)
	}
}
