# polyglot-covers: julia.runtime.scoped-values-across-tasks

using Test
using Base.ScopedValues

const request_id = ScopedValue(:default)

@testset "ScopedValue 动态范围传播到子 Task 并在退出后恢复" begin
    @test request_id[] === :default
    result = with(request_id => :request_42) do
        child = @async request_id[]
        return request_id[], fetch(child)
    end
    @test result == (:request_42, :request_42)
    @test request_id[] === :default
end
