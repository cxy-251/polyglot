// polyglot-family: modules_packages_and_loading
// polyglot-concept: modules_imports_linkage_and_live_bindings
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 01_toolchain_source_and_testing/test_002_internal_and_external_test_packages_test.go
//
// 共同问题：import alias 是否创建新模块实例；可变导出是否共享；局部重绑定影响谁。
// 对照观察：alias 只改变当前文件 package 名；同一 import path 在一个程序中只有一个初始化实例。
package modules_imports_linkage_and_live_bindings

import (
	httpalias "net/http"
	"testing"
)

func TestImportAliasDoesNotClonePackageState(t *testing.T) {
	original := httpalias.DefaultClient
	t.Cleanup(func() { httpalias.DefaultClient = original })
	replacement := &httpalias.Client{}
	httpalias.DefaultClient = replacement
	if httpalias.DefaultClient != replacement {
		t.Fatal("alias 只改变当前文件绑定，仍访问 net/http 的同一导出状态")
	}
	local := httpalias.DefaultClient
	local = original
	if httpalias.DefaultClient != replacement || local != original {
		t.Fatal("本地变量重绑定不修改 package export")
	}
}
