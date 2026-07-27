// polyglot-covers: go.packages.import-cycles
package packagesmodules_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestImportCycleIsRejectedBeforeExecution(t *testing.T) {
	root := t.TempDir()
	files := map[string]string{
		"go.mod": "module example.test/cycle\n\ngo 1.26.0\n",
		"a/a.go": "package a\nimport _ \"example.test/cycle/b\"\n",
		"b/b.go": "package b\nimport _ \"example.test/cycle/a\"\n",
	}
	for name, content := range files {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	command := exec.Command("go", "list", "./...")
	command.Dir = root
	command.Env = append(command.Environ(), "GOWORK=off")
	output, err := command.CombinedOutput()
	if err == nil || !strings.Contains(string(output), "import cycle not allowed") {
		t.Fatalf("package import graph 必须无环: %s", output)
	}
}
