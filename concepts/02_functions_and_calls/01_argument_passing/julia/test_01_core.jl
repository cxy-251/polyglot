# polyglot-family: functions_and_calls
# polyglot-concept: argument_passing
# polyglot-related: languages/julia/language/03_scope_functions_closures_and_calls/
# polyglot-related+: test_020_argument_binding_and_mutation.jl
#
# 共同问题：参数传递复制什么；函数内重新绑定和修改可变对象怎样影响调用方。
# 对照观察：Julia 参数是新的 binding，指向同一传入值；重新绑定局部名不影响调用方，修改对象可见。

using Test

function update_argument!(items)
    push!(items, 2)
    items = [99]
    return items
end

@testset "binding 按共享值传递" begin
    source = [1]
    rebound = update_argument!(source)
    @test source == [1, 2]
    @test rebound == [99]
    @test rebound !== source
end
