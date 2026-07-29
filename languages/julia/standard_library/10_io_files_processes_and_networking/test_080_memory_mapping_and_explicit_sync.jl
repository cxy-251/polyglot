# polyglot-covers: julia.stdlib.memory-mapping-and-explicit-sync

using Test
using Mmap

@testset "Mmap 视图共享文件字节并通过 sync 显式持久化" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        path = joinpath(directory, "mapped.bin")
        open(path, "w+") do stream
            write(stream, zeros(UInt8, 4))
            flush(stream)
            seekstart(stream)
            mapped = Mmap.mmap(stream, Vector{UInt8}, 4)
            mapped[1] = 0x2a
            mapped[4] = 0xff
            @test mapped == UInt8[0x2a, 0x00, 0x00, 0xff]
            Mmap.sync!(mapped)
        end
        @test read(path) == UInt8[0x2a, 0x00, 0x00, 0xff]
    end
end
