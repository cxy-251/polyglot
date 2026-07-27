// polyglot-covers: go.encoding-json.streaming-and-unknown-fields
package serialization_test

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestDecoderStreamsValuesAndCanRejectUnknownFields(t *testing.T) {
	decoder := json.NewDecoder(strings.NewReader(`{"name":"go"} {"name":"next"}`))
	var first jsonRecord
	var second jsonRecord
	if err := decoder.Decode(&first); err != nil {
		t.Fatal(err)
	}
	if err := decoder.Decode(&second); err != nil || first.Name != "go" || second.Name != "next" {
		t.Fatalf("Decoder 可从一个 stream 依次读取 JSON values: %+v %+v %v", first, second, err)
	}
	strict := json.NewDecoder(strings.NewReader(`{"name":"go","unexpected":true}`))
	strict.DisallowUnknownFields()
	if err := strict.Decode(&first); err == nil {
		t.Fatal("默认忽略未知字段；边界 API 可启用 DisallowUnknownFields")
	}
}
