# polyglot-family: values_and_comparison
# polyglot-concept: identity_aliasing_and_copying
# polyglot-related: languages/julia/standard_library/08_collections_ranges_and_copying/
# polyglot-related+: test_064_shallow_copy_deepcopy_and_cycles.jl
#
# 共同问题：赋值、浅复制和深复制怎样保留或切断别名；身份是否等于内容相等。
# 对照观察：赋值复制 binding，copy 只重建外层容器，deepcopy 重建对象图并保留图内共享。

using Test

@testset "复制层次决定别名边界" begin
    inner = [1]
    source = [inner]
    alias = source
    shallow = copy(source)
    deep = deepcopy(source)
    @test alias === source
    @test shallow !== source
    @test shallow[1] === inner
    @test deep[1] !== inner
    @test deep == source
end
