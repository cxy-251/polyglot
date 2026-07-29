# 共同问题：locale capability 怎样检测，进程环境状态怎样隔离。
# 输入：Encoding.find(:locale)、显式 child environment 和父进程 ENV；观察：可用 encoding 与状态不泄漏。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/
# polyglot-related+: test_077_locale_capabilities_and_process_scope.rb

require "assertions"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

original = ENV["LC_ALL"]
%w[C C.UTF-8].each do |locale|
  stdout, stderr, status = H.ruby_command(
    "-e",
    "print [ENV.fetch('LC_ALL'), Encoding.find('locale').name].join('|')",
    environment: {"LC_ALL" => locale}
  )
  A.truth(status.success?, stderr)
  returned_locale, encoding_name = stdout.split("|", 2)
  A.equal(locale, returned_locale)
  A.truth(Encoding.find(encoding_name).is_a?(Encoding))
end
A.equal(original, ENV["LC_ALL"])

# locale 名称及可用集合取决于部署平台；先探测，不把宿主机清单当作语言保证。
A.truth(Encoding.find("locale").is_a?(Encoding))

A.done
