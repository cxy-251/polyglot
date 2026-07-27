// polyglot-covers: go.modules.replace-and-workspace
package packagesmodules_test

import (
	"encoding/json"
	"os/exec"
	"path/filepath"
	"runtime"
	"testing"
)

func TestWorkspaceSelectsBothLocalModules(t *testing.T) {
	_, filename, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(filename), "..", "..", "..", ".."))
	command := exec.Command("go", "work", "edit", "-json")
	command.Dir = root
	output, err := command.Output()
	if err != nil {
		t.Fatal(err)
	}
	var workspace struct {
		Use []struct{ DiskPath string }
	}
	if err := json.Unmarshal(output, &workspace); err != nil {
		t.Fatal(err)
	}
	if len(workspace.Use) != 2 {
		t.Fatalf("workspace 应选择纵向与横向两个本地 module: %+v", workspace.Use)
	}
	// go.mod 的 replace 与 go.work 的 use 都重定向解析，但 workspace 不应发布为模块依赖。
}
