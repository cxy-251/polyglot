// polyglot-covers: go.os-exec.stdio-exit-context
package ioworkflows_test

import (
	"bytes"
	"context"
	"errors"
	"os/exec"
	"testing"
)

func TestCommandSeparatesStreamsAndReportsExitStatus(t *testing.T) {
	command := exec.Command("sh", "-c", "printf out; printf err >&2; exit 7")
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr
	err := command.Run()
	var exitError *exec.ExitError
	if !errors.As(err, &exitError) || exitError.ExitCode() != 7 ||
		stdout.String() != "out" || stderr.String() != "err" {
		t.Fatalf("Command 显式连接 stdio，并以 ExitError 表达非零状态: %q %q %v", &stdout, &stderr, err)
	}

	contextValue, cancel := context.WithCancel(context.Background())
	cancel()
	err = exec.CommandContext(contextValue, "sh", "-c", "printf unreachable").Run()
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("启动前取消的 context 阻止子进程执行: %v", err)
	}
}
