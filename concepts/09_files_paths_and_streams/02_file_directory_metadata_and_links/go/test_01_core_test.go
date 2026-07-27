// polyglot-family: files_paths_and_streams
// polyglot-concept: file_directory_metadata_and_links
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 12_io_files_paths_processes_and_environment/test_092_temporary_files_and_metadata_test.go
//
// 共同问题：文件与目录元数据如何取得；链接本身和目标怎样区分；资源如何可靠关闭。
// 对照观察：Stat 跟随 symlink，Lstat 检查链接目录项；os.File.Close 返回必须处理的 error。
package file_directory_metadata_and_links

import (
	"os"
	"path/filepath"
	"testing"
)

func TestStatAndLstatObserveDifferentObjects(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "target.txt")
	if err := os.WriteFile(target, []byte("data"), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "link")
	if err := os.Symlink("target.txt", link); err != nil {
		t.Skipf("当前文件系统不支持 symlink: %v", err)
	}
	followed, err := os.Stat(link)
	if err != nil {
		t.Fatal(err)
	}
	entry, err := os.Lstat(link)
	if err != nil || followed.Size() != 4 || entry.Mode()&os.ModeSymlink == 0 {
		t.Fatalf("Stat 观察目标，Lstat 观察链接目录项: %+v %+v %v", followed, entry, err)
	}
}
