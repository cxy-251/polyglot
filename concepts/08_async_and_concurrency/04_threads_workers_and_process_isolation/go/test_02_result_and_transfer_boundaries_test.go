// polyglot-family: async_and_concurrency
// polyglot-concept: threads_workers_and_process_isolation
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 12_io_files_paths_processes_and_environment/test_096_subprocess_stdio_exit_and_context_test.go
//
// 共同问题：隔离执行单元怎样传回结果；对象是共享、复制还是序列化。
// 对照观察：os/exec 子进程不共享 Go heap，结果必须通过 stdio、文件、socket 等显式协议传输。
package threads_workers_and_process_isolation

import (
	"os/exec"
	"testing"
)

func TestSubprocessResultCrossesAByteStreamBoundary(t *testing.T) {
	output, err := exec.Command("sh", "-c", "printf 42").Output()
	if err != nil || string(output) != "42" {
		t.Fatalf("进程结果通过 stdout bytes 传回，需要调用方解析: %q %v", output, err)
	}
}
