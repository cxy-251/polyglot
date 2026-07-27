// polyglot-covers: go.archive-compress-hash-crypto-rand
package networkworkflows_test

import (
	"archive/zip"
	"bytes"
	"compress/gzip"
	"crypto/rand"
	"crypto/sha256"
	"io"
	"testing"
)

func TestArchiveCompressionHashAndSecureRandomHaveSeparateRoles(t *testing.T) {
	var compressed bytes.Buffer
	gzipWriter := gzip.NewWriter(&compressed)
	_, _ = gzipWriter.Write([]byte("payload"))
	if err := gzipWriter.Close(); err != nil {
		t.Fatal(err)
	}
	gzipReader, err := gzip.NewReader(&compressed)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := io.ReadAll(gzipReader)
	if err != nil || string(decoded) != "payload" {
		t.Fatalf("compress/gzip 处理一个压缩 stream: %q %v", decoded, err)
	}

	var archive bytes.Buffer
	zipWriter := zip.NewWriter(&archive)
	entry, err := zipWriter.Create("file.txt")
	if err != nil {
		t.Fatal(err)
	}
	_, _ = entry.Write(decoded)
	if err := zipWriter.Close(); err != nil {
		t.Fatal(err)
	}
	if sha256.Sum256(decoded) == ([32]byte{}) {
		t.Fatal("hash 提供内容摘要，不提供保密性")
	}
	random := make([]byte, 16)
	if _, err := rand.Read(random); err != nil {
		t.Fatalf("crypto/rand 从系统安全随机源填充完整 buffer: %v", err)
	}
}
