// polyglot-covers: go.os.temporary-files-and-metadata
package ioworkflows_test

import (
	"os"
	"path/filepath"
	"testing"
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
