// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 09_packages_modules_imports_and_initialization/test_067_module_path_and_go_mod_test.go
//
// 共同问题：包名如何解析到代码；公开 API 边界在哪里；版本是否改变 import identity。
// 对照观察：Go 由 module path、go.mod 和 import path 解析 package；大写标识符导出，internal 限制父树。
package package_resolution_exports_and_visibility

import (
	"runtime/debug"
	"strings"
	"testing"
)

func TestBuildInfoReportsResolvedMainModule(t *testing.T) {
	info, ok := debug.ReadBuildInfo()
	if !ok || info.Main.Path != "polyglot.local/c" {
		t.Fatalf("当前 package 由 concepts/go.mod 的 module path 定位: %+v", info)
	}
	if strings.Contains(info.Main.Path, "/v1") {
		t.Fatal("v0/v1 module path 不带 major suffix；v2+ 通常把 /vN 纳入 import identity")
	}
	// 未导出标识符不能跨 package selector 访问；该边界在编译期生效。
}
