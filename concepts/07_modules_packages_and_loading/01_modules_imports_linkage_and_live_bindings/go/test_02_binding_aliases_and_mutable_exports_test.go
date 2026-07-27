// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 09_packages_modules_imports_and_initialization/test_066_package_initialization_and_blank_import_test.go
//
// 共同问题：import alias 是否创建新模块实例；可变导出是否共享；局部重绑定影响谁。
// 对照观察：alias 只改变当前文件 package 名；同一 import path 在一个程序中只有一个初始化实例。
package modules_imports_linkage_and_live_bindings

import (
	"testing"

	alias "polyglot.local/concepts/07_modules_packages_and_loading/01_modules_imports_linkage_and_live_bindings/go/support/state"
)

func TestImportAliasDoesNotClonePackageState(t *testing.T) {
	original := alias.Counter
	t.Cleanup(func() { alias.SetCounter(original) })
	alias.SetCounter(12)
	if alias.Counter != 12 {
		t.Fatal("import alias 是文件级名称，不创建 package 状态副本")
	}
	local := alias.Counter
	local = 99
	if alias.Counter != 12 || local != 99 {
		t.Fatal("本地变量重绑定不修改 package export")
	}
}
