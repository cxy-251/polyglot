// polyglot-covers: go.slog-template-flag
package networkworkflows_test

import (
	"bytes"
	"flag"
	"io"
	"log/slog"
	"strings"
	"testing"
	"text/template"
)

func TestStructuredLoggingTemplatesAndFlagSetsAreComposable(t *testing.T) {
	var logs bytes.Buffer
	handler := slog.NewJSONHandler(&logs, &slog.HandlerOptions{
		ReplaceAttr: func(groups []string, attribute slog.Attr) slog.Attr {
			if attribute.Key == slog.TimeKey {
				return slog.Attr{}
			}
			return attribute
		},
	})
	slog.New(handler).Info("ready", "course", "go")
	if !strings.Contains(logs.String(), `"course":"go"`) {
		t.Fatalf("slog 保留结构化 attribute: %s", &logs)
	}

	var rendered bytes.Buffer
	parsed := template.Must(template.New("welcome").Parse("Hello, {{.}}"))
	if err := parsed.Execute(&rendered, "Gopher"); err != nil || rendered.String() != "Hello, Gopher" {
		t.Fatalf("template 分离解析与执行: %q %v", &rendered, err)
	}

	flags := flag.NewFlagSet("course", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	count := flags.Int("count", 1, "number of runs")
	if err := flags.Parse([]string{"-count=3"}); err != nil || *count != 3 {
		t.Fatalf("独立 FlagSet 避免污染进程全局 CommandLine: %d %v", *count, err)
	}
}
