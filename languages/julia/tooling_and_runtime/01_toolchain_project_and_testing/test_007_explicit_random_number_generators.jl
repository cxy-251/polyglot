# polyglot-covers: julia.toolchain.explicit-random-generators

using Test
using Random

@testset "显式 RNG 使测试不依赖进程默认随机状态" begin
    first_rng = Xoshiro(0x251)
    second_rng = Xoshiro(0x251)
    @test rand(first_rng, UInt, 4) == rand(second_rng, UInt, 4)
    @test rand(Xoshiro(1), 1:100, 5) != rand(Xoshiro(2), 1:100, 5)
end
