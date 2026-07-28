# polyglot-covers: julia.stdlib.shallow-copy-deepcopy-and-cycles

using Test

@testset "copy 保留嵌套别名，deepcopy 重建图并保持内部 cycle" begin
    inner = [1]
    original = Any[inner]
    shallow = copy(original)
    deep = deepcopy(original)
    @test shallow !== original
    @test shallow[1] === inner
    @test deep[1] !== inner
    cyclic = Any[]
    push!(cyclic, cyclic)
    cloned = deepcopy(cyclic)
    @test cloned !== cyclic
    @test cloned[1] === cloned
end
