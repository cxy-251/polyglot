# 共同问题：feature 怎样解析，模块的 public 和 private 常量怎样控制可见性。
# 输入：$LOAD_PATH、require、Module API 和 private_constant；观察：搜索顺序、显式命名空间及访问失败。
# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_063_require_load_autoload_and_failure_cache.rb

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("package-visibility")
FileUtils.mkdir_p(root)
File.write(
  File.join(root, "polyglot_package.rb"),
  "module PolyglotPackage; PUBLIC = 42; PRIVATE = 7; private_constant :PRIVATE; end\n"
)
$LOAD_PATH.unshift(root)
begin
  A.truth(require("polyglot_package"))
  A.equal(42, PolyglotPackage::PUBLIC)
  A.raises(NameError) { PolyglotPackage::PRIVATE }
  A.equal(7, PolyglotPackage.const_get(:PRIVATE, false))
  A.falsey(Object.const_defined?(:PUBLIC, false))
ensure
  $LOAD_PATH.delete(root)
end

A.done
