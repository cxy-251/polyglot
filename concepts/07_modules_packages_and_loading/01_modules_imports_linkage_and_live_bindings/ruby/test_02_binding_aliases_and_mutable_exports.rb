# 共同问题：导入 alias 在导出状态改变后仍是 live binding 还是快照。
# 输入：Module alias、标量读取、可变 Array 和 writer；观察：常量 alias 身份、标量快照及共享导出。
# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/ruby/language/04_classes_modules_and_lookup/
# polyglot-related+: test_032_class_variables_class_state_and_constants.rb

require "assertions"

A = PolyglotAssertions

exports = Module.new do
  @value = 1
  @items = []

  class << self
    attr_accessor :value
    attr_reader :items
  end
end

alias_value = exports
scalar_snapshot = exports.value
items_alias = exports.items
exports.value = 2
exports.items << :ruby

A.same(exports, alias_value)
A.equal(1, scalar_snapshot)
A.equal(2, alias_value.value)
A.same(items_alias, exports.items)
A.equal([:ruby], items_alias)

A.done
