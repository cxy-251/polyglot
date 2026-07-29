# polyglot-family: values_and_comparison
# polyglot-concept: truthiness
# polyglot-related: languages/julia/language/02_values_types_missing_and_numbers/
# polyglot-related+: test_009_type_lattice_and_runtime_type_queries.jl
#
# 共同问题：零、空集合和空值如何进入条件；逻辑运算是否返回原操作数。
# 对照观察：Julia 条件和 &&/|| 左操作数要求 Bool，不提供容器或数值的隐式真假协议。

using Test

@testset "条件位置只接受 Bool" begin
    @test (true && 7) == 7
    @test (false || "fallback") == "fallback"
    @test_throws TypeError if 0
        :unreachable
    end
    @test_throws TypeError if Int[]
        :unreachable
    end
    @test isempty(Int[])
end
