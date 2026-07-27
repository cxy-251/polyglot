// polyglot-covers: go.io.pipe-and-scanner
package ioworkflows_test

import (
	"bufio"
	"io"
	"slices"
	"testing"
)

func TestPipeProvidesStreamingBackpressureAndScannerTokenization(t *testing.T) {
	reader, writer := io.Pipe()
	go func() {
		_, err := writer.Write([]byte("first\nsecond\n"))
		_ = writer.CloseWithError(err)
	}()
	scanner := bufio.NewScanner(reader)
	lines := []string{}
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(lines, []string{"first", "second"}) {
		t.Fatalf("Pipe 同步生产与消费；Scanner 按 split function 产出 token: %v", lines)
	}
}
