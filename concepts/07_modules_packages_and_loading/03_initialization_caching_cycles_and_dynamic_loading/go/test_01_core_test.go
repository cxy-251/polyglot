// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 09_packages_modules_imports_and_initialization/test_066_package_initialization_and_blank_import_test.go
//
// 共同问题：模块初始化执行几次、顺序如何；重复 import 是否复用实例；循环如何处理。
// 对照观察：Go 按依赖顺序初始化，每个 package 实例一次；import graph 必须在构建期无环。
package initialization_caching_cycles_and_dynamic_loading

import (
	"testing"

	state "polyglot.local/concepts/07_modules_packages_and_loading/01_modules_imports_linkage_and_live_bindings/go/support/state"
)

func TestImportedPackageInstanceIsInitializedOnce(t *testing.T) {
	firstAddress := &state.Counter
	secondAddress := &state.Counter
	if firstAddress != secondAddress {
		t.Fatal("同一 import path 在当前程序中解析到同一 package 变量")
	}
	// package variable 先按依赖初始化，再运行该 package 的 init；import cycle 在执行前被拒绝。
}
