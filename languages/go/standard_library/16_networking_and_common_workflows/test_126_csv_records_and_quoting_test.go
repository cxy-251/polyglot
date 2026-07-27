// polyglot-covers: go.encoding-csv.records-and-quoting
package networkworkflows_test

import (
	"bytes"
	"encoding/csv"
	"slices"
	"testing"
)

func TestCSVWriterQuotesFieldsAndReaderRestoresRecords(t *testing.T) {
	var buffer bytes.Buffer
	writer := csv.NewWriter(&buffer)
	if err := writer.Write([]string{"name", "a,b", "line\nbreak"}); err != nil {
		t.Fatal(err)
	}
	writer.Flush()
	if err := writer.Error(); err != nil {
		t.Fatal(err)
	}
	record, err := csv.NewReader(&buffer).Read()
	if err != nil || !slices.Equal(record, []string{"name", "a,b", "line\nbreak"}) {
		t.Fatalf("csv 处理 delimiter、quote 与嵌入换行，不应用 strings.Split 代替: %v %v", record, err)
	}
}
