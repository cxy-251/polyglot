# polyglot-covers: julia.language.lexical-scope-let-and-shadowing

using Test

function scoped_values()
    outer = 1
    inner = let outer = outer + 1
        outer * 10
    end
    return outer, inner
end

@testset "let 建立新的 lexical binding 而不修改外层变量" begin
    @test scoped_values() == (1, 20)
    @test !isdefined(Main, :outer)
end
