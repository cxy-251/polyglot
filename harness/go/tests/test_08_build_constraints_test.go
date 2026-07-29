// polyglot-harness: go.build_constraints
package goharness_test

import (
	"go/build"
	"os"
	"path/filepath"
	"testing"
)

func TestBuildConstraintsSelectFilesBeforeCompilation(t *testing.T) {
	directory := t.TempDir()
	linuxFile := filepath.Join(directory, "feature_linux.go")
	windowsFile := filepath.Join(directory, "feature_windows.go")
	source := []byte("package sample\n")
	if err := os.WriteFile(linuxFile, source, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(windowsFile, source, 0o600); err != nil {
		t.Fatal(err)
	}
	context := build.Default
	context.GOOS = "linux"
	matchedLinux, err := context.MatchFile(directory, filepath.Base(linuxFile))
	if err != nil {
		t.Fatal(err)
	}
	matchedWindows, err := context.MatchFile(directory, filepath.Base(windowsFile))
	if err != nil {
		t.Fatal(err)
	}
	if !matchedLinux || matchedWindows {
		t.Fatal("文件名后缀是 build constraint 的一部分")
	}
}
