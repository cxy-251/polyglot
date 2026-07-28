# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/julia/standard_library/09_text_data_dates_and_math/
# polyglot-related+: test_069_dates_periods_and_calendar_arithmetic.jl
#
# 共同问题：DST transition 和月底算术怎样处理；缺失时区数据库时如何表达能力边界。
# 对照观察：Julia 标准库不提供 IANA zone 类型；月份算术可执行，DST 需显式第三方能力且本课程不安装。

using Test
using Dates

@testset "标准库只保证无时区 calendar arithmetic" begin
    @test Date(2024, 1, 31) + Month(1) == Date(2024, 2, 29)
    @test Date(2023, 1, 31) + Month(1) == Date(2023, 2, 28)
    @test Base.find_package("TimeZones") === nothing
    @test !isdefined(Dates, :ZonedDateTime)
end
