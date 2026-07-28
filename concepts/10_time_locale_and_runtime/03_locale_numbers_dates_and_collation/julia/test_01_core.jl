# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_051_interpolation_show_and_printf_formatting.jl
#
# 共同问题：数字、日期格式和文本排序是否隐式读取进程 locale。
# 对照观察：Julia Printf/parse 使用程序指定格式，默认字符串排序不是 locale collation。

using Test
using Dates
using Printf

@testset "核心格式化不伪装成 locale-aware API" begin
    @test @sprintf("%.1f", 1.5) == "1.5"
    @test parse(Float64, "1.5") == 1.5
    @test Date("2024-07-28", dateformat"yyyy-mm-dd") == Date(2024, 7, 28)
    @test sort(["ä", "z"]) == ["z", "ä"]
end
