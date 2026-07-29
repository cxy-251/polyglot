# 共同问题：无效程序在哪个阶段失败，语法、加载和运行期错误怎样区分。
# 输入：语法错误、缺失 feature 和错误操作数；观察：独立语法检查状态、LoadError 与 TypeError。
# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/ruby/language/08_exceptions_resources_and_loading/
# polyglot-related+: test_064_process_exit_syntax_and_load_failures.rb

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

stdout, stderr, status = H.ruby_command("-c", "-e", "def broken(")
A.falsey(status.success?)
A.equal("", stdout)
A.matches(/syntax error/i, stderr)

A.raises(LoadError) { require "polyglot_feature_that_does_not_exist" }
A.raises(TypeError) { 1 + "1" }
A.raises(NoMethodError) { Object.new.polyglot_missing_method }

A.done
