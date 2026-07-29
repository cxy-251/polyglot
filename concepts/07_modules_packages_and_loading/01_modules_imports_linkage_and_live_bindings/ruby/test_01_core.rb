# 共同问题：require 导入什么，初始化怎样缓存，不同消费者共享哪个对象。
# 输入：临时 feature、Module 常量、两次 require 和可变导出；观察：布尔返回、loaded feature 缓存及共享身份。
# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_063_require_load_and_feature_cache.rb

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("module-live")
FileUtils.mkdir_p(root)
feature = File.join(root, "polyglot_live.rb")
File.write(feature, "module PolyglotLive; VALUES = []; end\n")
$LOAD_PATH.unshift(root)
begin
  A.truth(require("polyglot_live"))
  A.falsey(require("polyglot_live"))
  first = PolyglotLive
  second = Object.const_get(:PolyglotLive)
  A.same(first, second)
  first::VALUES << :ruby
  A.equal([:ruby], second::VALUES)
  A.includes($LOADED_FEATURES, feature)
ensure
  $LOAD_PATH.delete(root)
end

A.done
