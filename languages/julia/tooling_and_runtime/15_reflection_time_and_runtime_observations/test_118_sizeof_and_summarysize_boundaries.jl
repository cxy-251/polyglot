# polyglot-covers: julia.runtime.sizeof-and-summarysize-boundaries

using Test

@testset "sizeof 与 summarysize 观察层不同且只对锁定实现解释" begin
    values = [1, 2, 3]
    payload_bytes = sizeof(Int) * length(values)
    @test sizeof(values) == payload_bytes
    @test Base.summarysize(values) >= payload_bytes
    @test sizeof("α") == ncodeunits("α")
    @test Base.summarysize("α") >= sizeof("α")
end
