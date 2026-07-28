# polyglot-family: values_and_comparison
# polyglot-concept: null_missing_and_optional_values
# polyglot-related: languages/julia/language/02_values_types_missing_and_numbers/
# polyglot-related+: test_011_missing_propagation_and_coalescing.jl
#
# 共同问题：值缺席与数据未知是否为同一状态；调用方怎样缩窄或提供默认值。
# 对照观察：nothing 表示缺席，missing 表示未知并传播；Union 类型和 coalesce/something 显式处理。

using Test

@testset "Nothing 与 Missing 不可互换" begin
    optional::Union{Nothing,Int} = nothing
    @test isnothing(optional)
    @test ismissing(missing + 1)
    @test coalesce(missing, 9) == 9
    @test something(nothing, 7) == 7
    @test coalesce(nothing, 9) === nothing
end
