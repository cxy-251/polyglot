# polyglot-family: errors_and_resources
# polyglot-concept: resource_cleanup
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_055_do_block_resource_cleanup.jl
#
# 共同问题：资源在正常返回和异常传播时如何可靠释放。
# 对照观察：Julia 的 open do block 把资源作用域绑定到回调，两个退出路径都会关闭流。

using Test

@testset "do block 覆盖正常与异常退出" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        path = joinpath(directory, "value.txt")
        normal_stream = Ref{IO}()
        open(path, "w") do io
            normal_stream[] = io
            write(io, "ok")
        end
        @test !isopen(normal_stream[])
        failing_stream = Ref{IO}()
        @test_throws ErrorException open(path, "a") do io
            failing_stream[] = io
            error("stop")
        end
        @test !isopen(failing_stream[])
    end
end
