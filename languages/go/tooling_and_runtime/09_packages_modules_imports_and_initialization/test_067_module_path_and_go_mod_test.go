// polyglot-covers: go.modules.path-and-go-mod
package packagesmodules_test

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestGoModDeclaresModuleIdentityAndLanguageVersion(t *testing.T) {
	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("无法定位课程文件")
	}
	moduleFile := filepath.Clean(filepath.Join(filepath.Dir(filename), "..", "..", "go.mod"))
	content, err := os.ReadFile(moduleFile)
	if err != nil {
		t.Fatal(err)
	}
	text := string(content)
	if !strings.Contains(text, "module polyglot.local/go-course") ||
		!strings.Contains(text, "go 1.26.0") {
		t.Fatalf("go.mod 同时声明 module path 与最低语言版本: %s", text)
	}
}
