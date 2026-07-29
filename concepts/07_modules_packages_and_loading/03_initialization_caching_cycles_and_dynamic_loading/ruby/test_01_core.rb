# 共同问题：初始化何时运行、怎样缓存，Ruby 和 C feature 如何动态加载。
# 输入：require、load、$LOADED_FEATURES 和仓库 C Extension；观察：一次缓存、显式重执行及动态模块 API。
# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_063_require_load_and_feature_cache.rb

require "assertions"
require "fileutils"
require "helpers"
require "polyglot_native"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("initialization")
FileUtils.mkdir_p(root)
feature = File.join(root, "polyglot_init.rb")
File.write(feature, "$polyglot_init_runs = ($polyglot_init_runs || 0) + 1\n")
$LOAD_PATH.unshift(root)
begin
  A.truth(require("polyglot_init"))
  A.falsey(require("polyglot_init"))
  A.equal(1, $polyglot_init_runs)
  A.truth(load(feature))
  A.equal(2, $polyglot_init_runs)
  A.equal(42, PolyglotNative.add(20, 22))
ensure
  $LOAD_PATH.delete(root)
  $polyglot_init_runs = nil
end

A.done
