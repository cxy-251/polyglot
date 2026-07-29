# 共同问题：成功取得的资源怎样在正常返回和异常退出时都被释放。
# 输入：真实文件、block 形式 open、异常和 ensure；观察：关闭状态、返回值与原异常传播。
# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_061_block_resources_and_nested_ensure.rb

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

path = H.temporary_path("cleanup.txt")
handle = nil
result = File.open(path, "w") do |file|
  handle = file
  file.write("ruby")
end
A.equal(4, result)
A.truth(handle.closed?)
A.equal("ruby", File.read(path))

error = A.raises(RuntimeError, "body") do
  File.open(path) { raise "body" }
end
A.equal("body", error.message)

A.done
