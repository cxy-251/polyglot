# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/julia/standard_library/09_text_data_dates_and_math/
# polyglot-related+: test_069_dates_periods_and_calendar_arithmetic.jl
#
# 共同问题：calendar arithmetic 怎样处理月份长度；Date 与 DateTime 是否携带时区。
# 对照观察：Dates 按公历 period 运算；DateTime 是无时区 civil time，标准库不提供 IANA zone 类型。

using Test
using Dates

@testset "公历日期与无时区 DateTime 明确分层" begin
    @test Date(2024, 2, 28) + Day(1) == Date(2024, 2, 29)
    @test Date(2023, 2, 28) + Day(1) == Date(2023, 3, 1)
    @test Date(2024, 1, 31) + Month(1) == Date(2024, 2, 29)
    value = DateTime(2024, 1, 1, 12)
    @test value + Hour(2) == DateTime(2024, 1, 1, 14)
    @test value isa DateTime
    @test !isdefined(Dates, :ZonedDateTime)
end
