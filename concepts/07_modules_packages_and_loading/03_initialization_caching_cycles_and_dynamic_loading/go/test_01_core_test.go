// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/go/language/04_functions_closures_defer_and_calls/
// polyglot-related+: test_032_package_init_and_function_boundary_test.go
//
// 共同问题：模块初始化执行几次、顺序如何；重复 import 是否复用实例；循环如何处理。
// 对照观察：Go 按依赖顺序初始化，每个 package 实例一次；import graph 必须在构建期无环。
package initialization_caching_cycles_and_dynamic_loading

import (
	"net/http"
	"testing"
)

func TestImportedPackageInstanceIsInitializedOnce(t *testing.T) {
	first := http.DefaultClient
	second := http.DefaultClient
	if first != second {
		t.Fatal("重复读取同一 import path 的导出变量观察同一 package 实例")
	}
	// package variable 先按依赖初始化，再运行该 package 的 init；import cycle 在执行前被拒绝。
}
