// polyglot-covers: go.archive-compress-hash-crypto-rand
package networkworkflows_test

import (
	"archive/zip"
	"bytes"
	"compress/gzip"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"testing"
)

func TestGzipRoundTrip(t *testing.T) {
	payload := []byte("payload")
	var compressed bytes.Buffer
	gzipWriter := gzip.NewWriter(&compressed)
	written, err := gzipWriter.Write(payload)
	if err != nil || written != len(payload) {
		t.Fatalf("gzip writer 必须报告完整写入或错误: %d %v", written, err)
	}
	if err := gzipWriter.Close(); err != nil {
		t.Fatalf("gzip writer close 写出 footer: %v", err)
	}
	gzipReader, err := gzip.NewReader(&compressed)
	if err != nil {
		t.Fatal(err)
	}
	decoded, readErr := io.ReadAll(gzipReader)
	closeErr := gzipReader.Close()
	if readErr != nil || closeErr != nil || !bytes.Equal(decoded, payload) {
		t.Fatalf("gzip reader 必须读到 EOF 并可靠关闭: %q read=%v close=%v", decoded, readErr, closeErr)
	}
}

func TestZipArchiveEntry(t *testing.T) {
	payload := []byte("payload")
	var archive bytes.Buffer
	zipWriter := zip.NewWriter(&archive)
	entry, err := zipWriter.Create("file.txt")
	if err != nil {
		t.Fatal(err)
	}
	written, err := entry.Write(payload)
	if err != nil || written != len(payload) {
		t.Fatalf("zip entry 必须报告完整写入或错误: %d %v", written, err)
	}
	if err := zipWriter.Close(); err != nil {
		t.Fatalf("zip writer close 写出中央目录: %v", err)
	}

	zipReader, err := zip.NewReader(bytes.NewReader(archive.Bytes()), int64(archive.Len()))
	if err != nil || len(zipReader.File) != 1 || zipReader.File[0].Name != "file.txt" {
		t.Fatalf("zip archive 保存命名 entry: %v %v", zipReader.File, err)
	}
	entryReader, err := zipReader.File[0].Open()
	if err != nil {
		t.Fatal(err)
	}
	decoded, readErr := io.ReadAll(entryReader)
	closeErr := entryReader.Close()
	if readErr != nil || closeErr != nil || !bytes.Equal(decoded, payload) {
		t.Fatalf("zip entry 可读取并可靠关闭: %q read=%v close=%v", decoded, readErr, closeErr)
	}
}

func TestHashAndSecureRandomHaveDifferentContracts(t *testing.T) {
	digest := sha256.Sum256([]byte("payload"))
	if actual := hex.EncodeToString(digest[:]); actual !=
		"239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5" {
		t.Fatalf("SHA-256 对确定输入产生确定摘要: %s", actual)
	}

	random := make([]byte, 16)
	count, err := rand.Read(random)
	if err != nil || count != len(random) {
		t.Fatalf("crypto/rand 从系统安全随机源填满请求 buffer: %d %v", count, err)
	}
}
