// polyglot-covers: go.statements.goto-scope-restrictions
package controlflow_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestGotoCannotJumpOverVariableDeclaration(t *testing.T) {
	directory := t.TempDir()
	sourcePath := filepath.Join(directory, "invalid.go")
	objectPath := filepath.Join(directory, "invalid.o")
	source := []byte("package invalid\nfunc f() { goto done; value := 1; done: _ = value }\n")
	if err := os.WriteFile(sourcePath, source, 0o600); err != nil {
		t.Fatal(err)
	}
	output, err := exec.Command("go", "tool", "compile", "-o", objectPath, sourcePath).CombinedOutput()
	if err == nil || !strings.Contains(string(output), "jumps over") {
		t.Fatalf("编译器应拒绝越过变量声明的 goto: %s", output)
	}
}
