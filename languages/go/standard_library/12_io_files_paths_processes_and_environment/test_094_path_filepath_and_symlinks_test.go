// polyglot-covers: go.paths.path-filepath-symlinks
package ioworkflows_test

import (
	"os"
	"path"
	"path/filepath"
	"testing"
)

func TestLexicalPathsAndFilesystemResolutionAreSeparate(t *testing.T) {
	if path.Join("https://host", "a", "..", "b") != "https:/host/b" {
		t.Fatal("path 做 slash 词法运算，不理解 URL scheme；URL 应使用 net/url")
	}
	root := t.TempDir()
	target := filepath.Join(root, "target")
	if err := os.WriteFile(target, []byte("ok"), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "link")
	if err := os.Symlink("target", link); err != nil {
		t.Skipf("当前文件系统不支持 symlink: %v", err)
	}
	resolved, err := filepath.EvalSymlinks(link)
	if err != nil || resolved != target {
		t.Fatalf("Clean 只做词法处理；EvalSymlinks 查询真实文件系统: %q %v", resolved, err)
	}
}
