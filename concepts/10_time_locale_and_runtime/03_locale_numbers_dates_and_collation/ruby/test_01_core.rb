# 共同问题：locale 怎样影响数字、日期文本和 collation。
# 输入：显式 C locale 子进程、format、Float、strftime 和 String#<=>；观察：Ruby 的 locale 边界。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/
# polyglot-related+: test_077_locale_capabilities_and_process_scope.rb

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

code = <<~'RUBY'
  values = [
    format("%.2f", 1234.5),
    Float("1234.5"),
    Time.utc(2026, 7, 29).strftime("%A %B"),
    ["\u{E4}", "a", "Z"].sort.join(",")
  ]
  print values.join("|")
RUBY
stdout, stderr, status = H.ruby_command("-e", code, environment: {"LC_ALL" => "C"})
A.truth(status.success?, stderr)
A.equal("1234.50|1234.5|Wednesday July|Z,a,ä", stdout)
A.raises(ArgumentError) { Float("1234,5") }

# Core numeric conversion 和 String#<=> 不提供 locale-sensitive 变体。
A.equal(-1, "Z" <=> "a")

A.done
