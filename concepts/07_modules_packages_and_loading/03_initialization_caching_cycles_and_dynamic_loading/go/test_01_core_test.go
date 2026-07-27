// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/go/language/04_functions_closures_defer_and_calls/
// polyglot-related+: test_032_package_init_and_function_boundary_test.go
//
// 共同问题：模块初始化执行几次、顺序如何；重复 import 是否复用实例；循环如何处理。
// 对照观察：Go 按依赖顺序初始化，每个 package 实例一次；import graph 必须在构建期无环。
package initialization_caching_cycles_and_dynamic_loading

import (
	"slices"
	"testing"

	"polyglot.local/c/07_modules_packages_and_loading/03_initialization_caching_cycles_and_dynamic_loading/go/support/init"
)

func TestPackageVariablesAndInitRunOncePerPackageInstance(t *testing.T) {
	first := initstate.Events
	second := initstate.Events
	expected := []string{"variable", "init"}
	if !slices.Equal(first, expected) || !slices.Equal(second, expected) {
		t.Fatalf("package variable 先初始化，init 随后执行，多个 selector 不会重复初始化: %v %v", first, second)
	}
	// 同一 import path 在程序中只有一个 package 实例；import cycle 在初始化前被构建器拒绝。
}
