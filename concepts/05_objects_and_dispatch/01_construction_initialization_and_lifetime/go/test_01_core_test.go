// polyglot-family: objects_and_dispatch
// polyglot-concept: construction_initialization_and_lifetime
// polyglot-related: languages/go/language/
// polyglot-related+: 06_structs_methods_embedding_and_interfaces/test_041_struct_values_and_layout_boundary_test.go
//
// 共同问题：对象怎样初始化、复制和结束生命周期；构造器是否由语言强制。
// 对照观察：Go struct 有可用零值和 literal；`NewX` 只是普通函数约定，GC 不提供确定析构时机。
package construction_initialization_and_lifetime

import "testing"

type connectionOptions struct {
	address string
	retries int
}

func newConnectionOptions(address string) *connectionOptions {
	return &connectionOptions{address: address, retries: 3}
}

func TestZeroValueLiteralAndConstructorConvention(t *testing.T) {
	var zero connectionOptions
	if zero.address != "" || zero.retries != 0 {
		t.Fatal("struct 零值递归来自字段零值")
	}
	configured := newConnectionOptions("loopback")
	copy := *configured
	copy.retries = 9
	if configured.retries != 3 {
		t.Fatal("普通构造函数可返回 pointer；解引用赋值仍复制 struct 值")
	}
	// 必须释放的外部资源使用 Close/defer；不能依赖 GC 或 finalizer 充当析构函数。
}
