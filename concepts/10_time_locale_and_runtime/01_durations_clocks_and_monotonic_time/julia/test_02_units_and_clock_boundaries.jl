# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/julia/standard_library/09_text_data_dates_and_math/
# polyglot-related+: test_069_dates_periods_and_calendar_arithmetic.jl
#
# 共同问题：不同 duration 单位是否隐式混为裸数字；calendar period 能否当固定秒数。
# 对照观察：Dates period 在类型中保留单位；Month 是日历步进，不等于固定数量的 Millisecond。

using Test
using Dates

@testset "固定单位与 calendar unit 不伪装等价" begin
    @test canonicalize(Millisecond(120_000)) == Minute(2)
    @test Dates.value(Hour(3)) == 3
    @test Hour(1) != Millisecond(1)
    @test typeof(Month(1)) === Month
    @test_throws MethodError convert(Millisecond, Month(1))
end
