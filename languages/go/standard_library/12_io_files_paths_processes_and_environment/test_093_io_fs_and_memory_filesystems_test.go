// polyglot-covers: go.io-fs.memory-filesystems
package ioworkflows_test

import (
	"io/fs"
	"testing"
	"testing/fstest"
)

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
