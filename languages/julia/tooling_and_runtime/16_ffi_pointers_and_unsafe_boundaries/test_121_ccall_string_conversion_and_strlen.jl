# polyglot-covers: julia.runtime.ccall-string-conversion-and-strlen

using Test

@testset "@ccall 根据声明的 ABI 类型转换字符串并调用 C" begin
    length_value = @ccall strlen("Julia"::Cstring)::Csize_t
    empty_length = @ccall strlen(""::Cstring)::Csize_t
    @test length_value == 5
    @test typeof(length_value) === Csize_t
    @test empty_length == 0
end
