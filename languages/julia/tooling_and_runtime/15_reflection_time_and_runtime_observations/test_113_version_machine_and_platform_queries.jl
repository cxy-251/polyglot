# polyglot-covers: julia.runtime.version-machine-and-platform-queries

using Test

@testset "VERSION 与 Sys 提供结构化运行时和目标平台信息" begin
    @test VERSION == v"1.12.6"
    @test Sys.WORD_SIZE in (32, 64)
    @test Sys.ARCH isa Symbol
    @test Sys.KERNEL isa Symbol
    @test Sys.islinux()
    @test Sys.CPU_THREADS >= 1
end
