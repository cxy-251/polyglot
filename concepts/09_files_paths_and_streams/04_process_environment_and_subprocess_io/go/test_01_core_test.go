// polyglot-family: files_paths_and_streams
// polyglot-concept: process_environment_and_subprocess_io
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 12_io_files_paths_processes_and_environment/test_096_subprocess_stdio_exit_and_context_test.go
//
// 共同问题：环境和 cwd 是进程全局还是调用局部；子进程 stdio、退出状态与取消如何表达。
// 对照观察：Cmd 可提供独立 Env/Dir 和 stream；非零状态是 ExitError，context 可终止子进程。
package process_environment_and_subprocess_io

import (
	"bytes"
	"errors"
	"os/exec"
	"testing"
)

func TestCommandReceivesExplicitEnvironmentAndSeparatesStreams(t *testing.T) {
	command := exec.Command("sh", "-c", "printf \"$COURSE\"; printf problem >&2; exit 3")
	command.Env = append(command.Environ(), "COURSE=go")
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	err := command.Run()
	var exitError *exec.ExitError
	if !errors.As(err, &exitError) || exitError.ExitCode() != 3 ||
		stdout.String() != "go" || stderr.String() != "problem" {
		t.Fatalf("Cmd 显式定义 env、stdio 与 status 边界: %q %q %v", &stdout, &stderr, err)
	}
}
