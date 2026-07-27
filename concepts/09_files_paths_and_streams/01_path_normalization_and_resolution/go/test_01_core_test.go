// polyglot-family: files_paths_and_streams
// polyglot-concept: path_normalization_and_resolution
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 12_io_files_paths_processes_and_environment/test_094_path_filepath_and_symlinks_test.go
//
// 共同问题：路径清理是词法还是访问文件系统；相对路径以什么基准解析；URL 是否属于文件路径。
// 对照观察：path 处理 slash 路径，filepath 使用目标 OS；Abs/Clean 不解析 symlink，EvalSymlinks 才查询磁盘。
package path_normalization_and_resolution

import (
	"os"
	"path"
	"path/filepath"
	"testing"
)

func TestLexicalNormalizationAndFilesystemResolutionDiffer(t *testing.T) {
	if path.Clean("a/./b/../c") != "a/c" {
		t.Fatal("path.Clean 只折叠词法 segment")
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
		t.Fatalf("EvalSymlinks 使用真实目录项解析: %q %v", resolved, err)
	}
}
