// polyglot-harness: go.examples_benchmarks_and_fuzz_seeds
package goharness_test

import (
	"fmt"
	"testing"

	course "polyglot.local/go-course/tests"
)

func ExampleAdd() {
	fmt.Println(course.Add(2, 4))
	// Output: 6
}

func BenchmarkAdd(b *testing.B) {
	for b.Loop() {
		_ = course.Add(2, 4)
	}
}

func FuzzAddIsCommutative(f *testing.F) {
	f.Add(2, 4)
	f.Fuzz(func(t *testing.T, left, right int) {
		if course.Add(left, right) != course.Add(right, left) {
			t.Fatal("整数加法应满足交换律")
		}
	})
}
