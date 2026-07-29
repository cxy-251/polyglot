// polyglot-covers: go.compress.gzip-stream-lifecycle
package networkworkflows_test

import (
	"bytes"
	"compress/gzip"
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
