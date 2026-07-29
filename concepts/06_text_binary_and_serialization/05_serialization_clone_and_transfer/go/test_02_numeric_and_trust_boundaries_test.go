// polyglot-family: text_binary_and_serialization
// polyglot-concept: serialization_clone_and_transfer
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 14_binary_encoding_and_serialization/test_108_json_tags_omitted_missing_and_null_test.go
//
// 共同问题：跨格式传输是否丢失数值精度；未知字段和不可信输入在哪里拒绝。
// 对照观察：interface JSON 默认用 float64；UseNumber 延迟选择，DisallowUnknownFields 强化 schema 边界。
package serialization_clone_and_transfer

import (
	"encoding/json"
	"io"
	"strings"
	"testing"
)

func TestDecoderOptionsMakeTrustPolicyExplicit(t *testing.T) {
	decoder := json.NewDecoder(io.LimitReader(strings.NewReader(`{"id":9007199254740993}`), 64))
	decoder.UseNumber()
	decoder.DisallowUnknownFields()
	var target struct {
		ID json.Number `json:"id"`
	}
	if err := decoder.Decode(&target); err != nil || target.ID.String() != "9007199254740993" {
		t.Fatalf("大小限制、schema 和数值策略应在解码边界组合: %+v %v", target, err)
	}
	strict := json.NewDecoder(strings.NewReader(`{"id":1,"extra":true}`))
	strict.DisallowUnknownFields()
	if err := strict.Decode(&target); err == nil {
		t.Fatal("未知字段应按 strict policy 拒绝")
	}
}
