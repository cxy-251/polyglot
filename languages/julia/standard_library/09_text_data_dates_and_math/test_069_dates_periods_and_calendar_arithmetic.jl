# polyglot-covers: julia.stdlib.dates-periods-and-calendar-arithmetic

using Test
using Dates

@testset "Dates 区分 calendar period、Date 和 DateTime" begin
    leap_day = Date(2024, 2, 29)
    @test leap_day + Year(1) == Date(2025, 2, 28)
    @test Date(2024, 1, 31) + Month(1) == Date(2024, 2, 29)
    moment = DateTime(2024, 1, 1, 12)
    @test moment + Hour(3) == DateTime(2024, 1, 1, 15)
    @test Dates.value(Date(2024, 1, 2) - Date(2024, 1, 1)) == 1
    @test (Date(2024, 1, 31) + Month(1)) + Month(1) == Date(2024, 3, 29)
    @test Date(2024, 1, 31) + Month(2) == Date(2024, 3, 31)
    @test !isdefined(Dates, :ZonedDateTime)
end
