# polyglot-covers: julia.language.do-block-resource-cleanup

using Test

@testset "open do block 在正常和异常路径后关闭流" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        path = joinpath(directory, "value.txt")
        stream_reference = Ref{IOStream}()
        open(path, "w") do stream
            stream_reference[] = stream
            write(stream, "value")
            @test isopen(stream)
        end
        @test !isopen(stream_reference[])
        @test read(path, String) == "value"
    end
end
