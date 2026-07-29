// polyglot-covers: go.control.labels-and-goto-boundaries
package controlflow_test

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestLabelsTargetAnEnclosingLoop(t *testing.T) {
	visited := []int{}
outer:
	for row := 0; row < 3; row++ {
		for column := 0; column < 3; column++ {
			if column == 1 {
				continue outer
			}
			visited = append(visited, row*10+column)
		}
	}
	if len(visited) != 3 || visited[2] != 20 {
		t.Fatalf("带标签 continue 跳到指定外层循环: %v", visited)
	}
}

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
