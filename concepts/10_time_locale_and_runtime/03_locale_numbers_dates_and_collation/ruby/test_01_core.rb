# 共同问题：locale 怎样影响数字、日期文本和 collation。
# 输入：隔离 C.UTF-8 locale、format、Float、strftime 和 String#<=>；观察：decimal dot、英文名称及非 locale 排序。
# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/ruby/tooling_and_runtime/16_advanced_runtime_and_compat/
# polyglot-related+: test_122_encoding_locale_and_timezone_boundary.rb

require "assertions"

A = PolyglotAssertions

A.equal("C.UTF-8", ENV.fetch("LC_ALL"))
A.equal("1234.50", format("%.2f", 1234.5))
A.near(1234.5, Float("1234.5"))
A.raises(ArgumentError) { Float("1234,5") }

date = Time.utc(2026, 7, 29)
A.equal("Wednesday July", date.strftime("%A %B"))
A.equal(-1, "Z" <=> "a")
A.equal(["Z", "a", "ä"], ["ä", "a", "Z"].sort)

A.done
