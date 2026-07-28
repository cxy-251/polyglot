# polyglot-family: text_binary_and_serialization
# polyglot-concept: binary_buffers_views_and_endianness
# polyglot-related: languages/julia/standard_library/10_io_files_processes_and_networking/
# polyglot-related+: test_073_iobuffer_position_seek_and_take.jl
#
# 共同问题：字节缓冲区怎样维护位置；多字节整数怎样显式跨主机端序。
# 对照观察：IOBuffer 将 cursor 与字节分离；hton/ntoh 显式转换网络序，reinterpret 不复制位模式。

using Test

@testset "缓冲位置和端序转换都可查询" begin
    buffer = IOBuffer()
    write(buffer, UInt8[0x01, 0x02])
    @test position(buffer) == 2
    seekstart(buffer)
    @test read(buffer) == UInt8[0x01, 0x02]
    value = UInt32(0x01020304)
    @test ntoh(hton(value)) == value
    @test reinterpret(UInt8, [UInt16(1)]) |> length == 2
end
