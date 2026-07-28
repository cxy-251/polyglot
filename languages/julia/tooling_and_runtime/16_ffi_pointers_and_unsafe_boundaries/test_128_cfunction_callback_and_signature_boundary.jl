# polyglot-covers: julia.runtime.cfunction-callback-and-signature-boundary

using Test

double_callback(value::Cint)::Cint = value * 2

@testset "@cfunction 固化 callback ABI，ccall 必须使用匹配签名" begin
    callback = @cfunction(double_callback, Cint, (Cint,))
    @test callback != C_NULL
    @test ccall(callback, Cint, (Cint,), 21) == 42
    @test Ptr{Cvoid}(callback) != C_NULL
end
