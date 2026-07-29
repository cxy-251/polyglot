# polyglot-covers: julia.language.do-block-resource-cleanup

using Test

@testset "open do block 在正常和异常路径后关闭流" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        path = joinpath(directory, "value.txt")
        normal_stream = Ref{IOStream}()
        open(path, "w") do stream
            normal_stream[] = stream
            write(stream, "value")
            @test isopen(stream)
        end
        @test !isopen(normal_stream[])
        @test read(path, String) == "value"
        failed_stream = Ref{IOStream}()
        @test_throws ErrorException open(path, "a") do stream
            failed_stream[] = stream
            error("body failed")
        end
        @test !isopen(failed_stream[])
    end
end
