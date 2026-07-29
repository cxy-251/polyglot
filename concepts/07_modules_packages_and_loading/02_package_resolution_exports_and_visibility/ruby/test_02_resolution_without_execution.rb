# 共同问题：能否在不执行初始化的情况下检查 feature 解析结果。
# 输入：临时 rb 文件、$LOAD_PATH candidate、$LOADED_FEATURES 和 require；观察：路径发现不执行，require 才运行。
# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/ruby/tooling_and_runtime/14_gems_bundler_and_rake/
# polyglot-related+: test_109_bundler_path_dependency_and_lock.rb

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("resolve-only")
FileUtils.mkdir_p(root)
feature = File.join(root, "polyglot_resolve.rb")
File.write(feature, "$polyglot_resolve_runs = ($polyglot_resolve_runs || 0) + 1\n")
$LOAD_PATH.unshift(root)
begin
  candidates = $LOAD_PATH.map { |directory| File.join(directory, "polyglot_resolve.rb") }
  A.equal(feature, candidates.find { File.file?(_1) })
  A.nil_value($polyglot_resolve_runs)
  A.falsey($LOADED_FEATURES.include?(feature))
  A.truth(require("polyglot_resolve"))
  A.equal(1, $polyglot_resolve_runs)
ensure
  $LOAD_PATH.delete(root)
  $polyglot_resolve_runs = nil
end

A.done
