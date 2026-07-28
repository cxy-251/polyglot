# polyglot-covers: julia.runtime.ccall-process-function-and-return-type

using Test

@testset "ccall 显式声明参数元组和返回 ABI 类型" begin
    process_id = ccall(:getpid, Cint, ())
    @test process_id > 0
    @test process_id == Cint(getpid())
    @test typeof(process_id) === Cint
end
