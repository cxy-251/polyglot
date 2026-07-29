// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/go/tooling_and_runtime/09_packages_modules_imports_and_initialization/
// polyglot-related+: test_065_package_namespace_exports_and_import_aliases_test.go
//
// 共同问题：import 建立值副本还是模块绑定；跨文件名称如何链接；导出状态更新是否可观察。
// 对照观察：Go import 绑定 package 名称，selector 每次读取 package 变量；普通赋值会复制当时的值。
package modules_imports_linkage_and_live_bindings

import (
	"net/http"
	"testing"
)

func TestPackageSelectorObservesCurrentExportedVariable(t *testing.T) {
	original := http.DefaultClient
	t.Cleanup(func() { http.DefaultClient = original })
	captured := http.DefaultClient
	http.DefaultClient = &http.Client{}
	if captured == http.DefaultClient || captured != original {
		t.Fatal("package selector 重新读取变量；赋给本地变量时才复制当前值")
	}
}

func TestImportAliasDoesNotClonePackageState(t *testing.T) {
	original := http.DefaultClient
	t.Cleanup(func() { http.DefaultClient = original })
	replacement := &http.Client{}
	http.DefaultClient = replacement
	if http.DefaultClient != replacement {
		t.Fatal("alias 只改变当前文件绑定，仍访问 net/http 的同一导出状态")
	}
	local := http.DefaultClient
	local = original
	if http.DefaultClient != replacement || local != original {
		t.Fatal("本地变量重绑定不修改 package export")
	}
}
