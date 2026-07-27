// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 09_packages_modules_imports_and_initialization/test_065_package_namespace_exports_and_import_aliases_test.go
//
// 共同问题：import 建立值副本还是模块绑定；跨文件名称如何链接；导出状态更新是否可观察。
// 对照观察：Go import 绑定 package 名称，selector 每次读取 package 变量；普通赋值会复制当时的值。
package modules_imports_linkage_and_live_bindings

import (
	"testing"

	statepkg "polyglot.local/concepts/07_modules_packages_and_loading/01_modules_imports_linkage_and_live_bindings/go/support/state"
)

func TestPackageSelectorObservesCurrentExportedVariable(t *testing.T) {
	original := statepkg.Counter
	t.Cleanup(func() { statepkg.SetCounter(original) })
	captured := statepkg.Counter
	statepkg.SetCounter(9)
	if captured == statepkg.Counter || captured != original || statepkg.Counter != 9 {
		t.Fatal("package selector 重新读取变量；赋给本地变量时才复制当前值")
	}
}
