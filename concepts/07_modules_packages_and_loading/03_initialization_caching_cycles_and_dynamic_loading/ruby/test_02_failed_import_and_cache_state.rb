# 共同问题：失败或循环初始化之后，feature cache 保留什么状态。
# 输入：首次失败后重试、两个循环 require 文件及预先定义的 Module；观察：失败不缓存、重试重跑和部分初始化。
# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_063_require_load_autoload_and_failure_cache.rb

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("failed-import")
FileUtils.mkdir_p(root)
failing = File.join(root, "polyglot_failing.rb")
File.write(failing, "$polyglot_attempts = ($polyglot_attempts || 0) + 1; raise 'first' if $polyglot_attempts == 1\n")
File.write(File.join(root, "polyglot_a.rb"), "module PolyglotCycle; A = 1; end; require 'polyglot_b'\n")
File.write(File.join(root, "polyglot_b.rb"), "require 'polyglot_a'; module PolyglotCycle; B = A + 1; end\n")
$LOAD_PATH.unshift(root)
begin
  A.raises(RuntimeError, "first") { require "polyglot_failing" }
  A.falsey($LOADED_FEATURES.include?(failing))
  A.truth(require("polyglot_failing"))
  A.equal(2, $polyglot_attempts)
  A.truth(require("polyglot_a"))
  A.equal(2, PolyglotCycle::B)
ensure
  $LOAD_PATH.delete(root)
  $polyglot_attempts = nil
end

A.done
