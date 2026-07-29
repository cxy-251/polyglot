// polyglot-covers: go.encoding-json.custom-streaming-and-schema-boundaries
package serialization_test

import (
	"encoding/json"
	"strings"
	"testing"
)

type upperText string

func (value upperText) MarshalJSON() ([]byte, error) {
	return json.Marshal(strings.ToUpper(string(value)))
}

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

func TestCustomMarshalerAndRawMessageControlRepresentation(t *testing.T) {
	payload := struct {
		Label upperText       `json:"label"`
		Extra json.RawMessage `json:"extra"`
	}{Label: "go", Extra: json.RawMessage(`{"version":1}`)}
	encoded, err := json.Marshal(payload)
	if err != nil || string(encoded) != `{"label":"GO","extra":{"version":1}}` {
		t.Fatalf("Marshaler 定义字段表示；RawMessage 延迟局部解码: %s %v", encoded, err)
	}
}
