# 共同问题：locale capability 怎样检测，进程环境状态怎样恢复。
# 输入：Encoding.find(:locale)、LC_ALL、child process 和 ensure；观察：启动时 locale encoding 与显式恢复。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/ruby/tooling_and_runtime/16_advanced_runtime_and_compat/
# polyglot-related+: test_122_encoding_locale_and_timezone_boundary.rb

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

A.equal("UTF-8", Encoding.find("locale").name)
original = ENV.fetch("LC_ALL")
begin
  ENV["LC_ALL"] = "C"
  A.equal("C", ENV.fetch("LC_ALL"))
ensure
  ENV["LC_ALL"] = original
end
A.equal("C.UTF-8", ENV.fetch("LC_ALL"))

stdout, stderr, status = H.ruby_command("-e", "print [ENV.fetch('LC_ALL'), Encoding.find('locale').name].join('|')")
A.truth(status.success?, stderr)
A.equal("C.UTF-8|UTF-8", stdout)

A.done
