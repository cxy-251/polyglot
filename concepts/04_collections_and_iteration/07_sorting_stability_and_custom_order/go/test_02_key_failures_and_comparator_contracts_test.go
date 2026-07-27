// polyglot-family: collections_and_iteration
// polyglot-concept: sorting_stability_and_custom_order
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_099_strconv_numeric_parsing_test.go
//
// 共同问题：key 提取失败时是否部分修改；不满足传递性的 comparator 会产生什么后果。
// 对照观察：Go sort API 的 comparator 不返回 error；需要失败的 key 应先解析，再开始原地排序。
package sorting_stability_and_custom_order

import (
	"cmp"
	"slices"
	"strconv"
	"testing"
)

func TestValidateKeysBeforeInPlaceSort(t *testing.T) {
	source := []string{"2", "invalid", "1"}
	keys := make([]int, len(source))
	for index, value := range source {
		parsed, err := strconv.Atoi(value)
		if err != nil {
			if !slices.Equal(source, []string{"2", "invalid", "1"}) {
				t.Fatal("预处理失败前不应修改输入")
			}
			return
		}
		keys[index] = parsed
	}
	slices.SortFunc(keys, cmp.Compare[int])
	t.Fatal("测试数据应在排序前触发解析失败")
}
