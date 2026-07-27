// polyglot-family: files_paths_and_streams
// polyglot-concept: streaming_buffering_and_backpressure
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 12_io_files_paths_processes_and_environment/test_091_pipe_and_scanner_test.go
//
// 共同问题：流如何表达短读写、缓冲和背压；完成与错误从哪里传播。
// 对照观察：Reader/Writer 允许部分进度；io.Pipe 的同步写入在 reader 消费前形成背压。
package streaming_buffering_and_backpressure

import (
	"bufio"
	"bytes"
	"io"
	"testing"
)

func TestPipeAndBufferedWriterExposeExplicitFlushBoundaries(t *testing.T) {
	reader, writer := io.Pipe()
	written := make(chan struct{})
	go func() {
		_, _ = writer.Write([]byte("payload"))
		close(written)
		_ = writer.Close()
	}()
	select {
	case <-written:
		t.Fatal("io.Pipe 没有内部 buffer，Write 应等待 Read")
	default:
	}
	payload, err := io.ReadAll(reader)
	if err != nil || string(payload) != "payload" {
		t.Fatalf("reader 消费后 writer 才完成: %q %v", payload, err)
	}
	<-written

	var destination bytes.Buffer
	buffered := bufio.NewWriter(&destination)
	_, _ = buffered.WriteString("queued")
	if destination.Len() != 0 {
		t.Fatal("缓冲写入在 Flush 前不一定到达下游")
	}
	if err := buffered.Flush(); err != nil || destination.String() != "queued" {
		t.Fatalf("Flush 是显式提交和错误边界: %q %v", &destination, err)
	}
}
