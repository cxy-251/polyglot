// polyglot-family: modules_packages_and_loading
// polyglot-concept: initialization_caching_cycles_and_dynamic_loading
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 09_packages_modules_imports_and_initialization/test_070_import_cycles_are_build_errors_test.go
//
// 共同问题：加载失败是否污染缓存；能否运行时重试、重新加载或动态选择模块。
// 对照观察：Go import 在构建期解析，失败不会形成运行时 module object；标准语言没有通用 reload。
package initialization_caching_cycles_and_dynamic_loading

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestFailedImportRemainsABuildErrorUntilSourceChanges(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"),
		[]byte("module example.test/missing\n\ngo 1.26.0\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	source := []byte("package missing\nimport _ \"example.test/absent\"\n")
	if err := os.WriteFile(filepath.Join(root, "missing.go"), source, 0o600); err != nil {
		t.Fatal(err)
	}
	command := exec.Command("go", "list", "-deps", ".")
	command.Dir = root
	command.Env = append(command.Environ(), "GOWORK=off", "GOPROXY=off")
	output, err := command.CombinedOutput()
	if err == nil || !strings.Contains(string(output), "example.test/absent") {
		t.Fatalf("缺失 import 是确定的构建失败，不是可捕获动态加载异常: %s", output)
	}
	// plugin 只在部分平台支持且不提供通用卸载/reload，不可作为跨平台 import 对应物。
}
