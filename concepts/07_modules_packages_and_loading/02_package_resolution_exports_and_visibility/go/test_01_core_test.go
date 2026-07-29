// polyglot-family: modules_packages_and_loading
// polyglot-concept: package_resolution_exports_and_visibility
// polyglot-related: languages/go/tooling_and_runtime/09_packages_modules_imports_and_initialization/
// polyglot-related+: test_066_package_initialization_and_blank_import_test.go
//
// 共同问题：解析元数据是否执行模块代码；发现 package 与运行初始化能否分离。
// 对照观察：go list 加载构建元数据但不运行 init；module download/replace 与程序执行是不同阶段。
package package_resolution_exports_and_visibility

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestGoListResolvesPackageWithoutRunningInit(t *testing.T) {
	root := t.TempDir()
	marker := filepath.Join(root, "initialized")
	module := "module example.test/list\n\ngo 1.26.0\n"
	source := fmt.Sprintf(`package sample
import "os"
func init() {
	if err := os.WriteFile(%q, []byte("ran"), 0600); err != nil {
		panic(err)
	}
}
`, marker)
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte(module), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "sample.go"), []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}
	command := exec.Command("go", "list", ".")
	command.Dir = root
	command.Env = append(command.Environ(), "GOWORK=off")
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("go list: %s", output)
	}
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatal("解析和类型检查 package 不执行 init")
	}
}
