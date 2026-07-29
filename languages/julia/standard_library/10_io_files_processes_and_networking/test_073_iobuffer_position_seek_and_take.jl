# polyglot-covers: julia.stdlib.iobuffer-position-seek-and-take

using Test

@testset "IOBuffer 显式维护读写位置并可转移缓冲字节" begin
    buffer = IOBuffer()
    write(buffer, "abc")
    @test position(buffer) == 3
    seekstart(buffer)
    @test read(buffer, Char) == 'a'
    @test position(buffer) == 1
    seekend(buffer)
    write(buffer, UInt8('d'))
    @test String(take!(buffer)) == "abcd"
    @test position(buffer) == 0
    write(buffer, UInt8[0x01, 0x02])
    seekstart(buffer)
    @test read(buffer, 2) == UInt8[0x01, 0x02]
    @test eof(buffer)
end
