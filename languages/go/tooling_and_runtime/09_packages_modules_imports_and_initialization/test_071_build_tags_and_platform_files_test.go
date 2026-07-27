// polyglot-covers: go.build.tags-and-platform-files
package packagesmodules_test

import (
	"go/build"
	"os"
	"path/filepath"
	"testing"
)

func TestExplicitTagsComposeWithPlatformSelection(t *testing.T) {
	root := t.TempDir()
	name := "feature_linux.go"
	source := []byte("//go:build linux && course\n\npackage feature\n")
	if err := os.WriteFile(filepath.Join(root, name), source, 0o600); err != nil {
		t.Fatal(err)
	}
	context := build.Default
	context.GOOS = "linux"
	matched, err := context.MatchFile(root, name)
	if err != nil {
		t.Fatal(err)
	}
	if matched {
		t.Fatal("未启用自定义 course tag 时文件应被排除")
	}
	context.BuildTags = []string{"course"}
	matched, err = context.MatchFile(root, name)
	if err != nil || !matched {
		t.Fatal("GOOS 后缀和 //go:build 表达式必须同时满足")
	}
}
