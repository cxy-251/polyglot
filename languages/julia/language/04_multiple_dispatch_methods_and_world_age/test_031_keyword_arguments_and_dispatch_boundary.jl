# polyglot-covers: julia.language.keyword-arguments-dispatch-boundary

using Test

render(value::Int; style = :plain) = (value, style)
render(value::AbstractString; style = :plain) = (value, style)

@testset "位置参数选择方法，keyword 在所选方法内部绑定" begin
    integer_method = which(render, (Int,))
    @test render(1; style = :hex) == (1, :hex)
    @test render("1"; style = :quoted) == ("1", :quoted)
    @test which(render, (Int,)) === integer_method
    @test_throws MethodError render(1; unknown = true)
end
