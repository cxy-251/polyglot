# 共同问题：无效程序在哪个阶段失败，语法、加载和运行期错误怎样区分。
# 输入：语法错误、缺失 feature 和错误操作数；观察：独立语法检查状态、LoadError 与 TypeError。
# polyglot-family: errors_and_resources
# polyglot-concept: contracts_assertions_and_failure_signaling
# polyglot-related: languages/ruby/tooling_and_runtime/13_command_parser_and_runtime/
# polyglot-related+: test_097_command_line_loading_warnings_and_option_parsing.rb

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
