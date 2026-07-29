# polyglot-covers: julia.runtime.c-calls-abi-types-and-callbacks

using Test

double_callback(value::Cint)::Cint = value * 2

@testset "@ccall 与 @cfunction 都要求调用方声明匹配的 C ABI" begin
    if Sys.isunix()
        length_value = @ccall strlen("Julia"::Cstring)::Csize_t
        empty_length = @ccall strlen(""::Cstring)::Csize_t
        @test length_value == 5
        @test typeof(length_value) === Csize_t
        @test empty_length == 0
    else
        @test_skip Sys.isunix()
    end
    callback = @cfunction(double_callback, Cint, (Cint,))
    @test callback != C_NULL
    @test ccall(callback, Cint, (Cint,), 21) == 42
    @test Ptr{Cvoid}(callback) != C_NULL
    # closure callback 依赖 LLVM trampoline 且并非所有架构可用；这里使用静态函数。
end
