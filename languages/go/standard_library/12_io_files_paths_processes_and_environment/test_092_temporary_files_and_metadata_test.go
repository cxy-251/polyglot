// polyglot-covers: go.files.metadata-and-abstract-filesystems
package ioworkflows_test

import (
	"io/fs"
	"os"
	"path/filepath"
	"testing"
	"testing/fstest"
)

func TestTemporaryFileLifecycleAndMetadata(t *testing.T) {
	path := filepath.Join(t.TempDir(), "record.txt")
	file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := file.WriteString("data"); err != nil {
		closeErr := file.Close()
		t.Fatalf("写入临时文件失败；关闭结果为 %v: %v", closeErr, err)
	}
	if err := file.Close(); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil || info.Size() != 4 || !info.Mode().IsRegular() {
		t.Fatalf("Stat 返回跟随链接后的 FileInfo: %+v %v", info, err)
	}
}

func TestFSAlgorithmsWorkAgainstAbstractFilesystem(t *testing.T) {
	files := fstest.MapFS{
		"docs/readme.txt": {Data: []byte("course")},
		"docs/notes.md":   {Data: []byte("notes")},
	}
	matches, err := fs.Glob(files, "docs/*.txt")
	if err != nil || len(matches) != 1 || matches[0] != "docs/readme.txt" {
		t.Fatalf("io/fs 使用 slash 分隔的相对路径，可测试真实磁盘之外的实现: %v %v", matches, err)
	}
}
