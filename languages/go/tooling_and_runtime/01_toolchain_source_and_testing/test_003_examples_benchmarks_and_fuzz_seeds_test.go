// polyglot-covers: go.testing.examples-benchmarks-fuzz-seeds
package toolchaintesting_test

import (
	"fmt"
	"testing"

	course "polyglot.local/go-course/tooling_and_runtime/01_toolchain_source_and_testing"
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
