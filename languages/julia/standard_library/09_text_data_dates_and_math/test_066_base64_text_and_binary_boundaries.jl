# polyglot-covers: julia.stdlib.base64-text-and-binary-boundaries

using Test
using Base64

@testset "Base64 在字节与 ASCII 文本之间编码而不是序列化对象" begin
    bytes = UInt8[0x00, 0xff, 0x10]
    encoded = base64encode(bytes)
    @test encoded == "AP8Q"
    @test base64decode(encoded) == bytes
    @test base64encode("Julia") == "SnVsaWE="
    @test String(base64decode("SnVsaWE=")) == "Julia"
end
