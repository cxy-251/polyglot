# polyglot-covers: julia.stdlib.base64-digests-and-hex-boundaries

using Test
using Base64
using SHA

@testset "Base64 和 hex 只编码字节；SHA digest 才计算内容摘要" begin
    bytes = UInt8[0x00, 0xff, 0x10]
    encoded = base64encode(bytes)
    @test encoded == "AP8Q"
    @test base64decode(encoded) == bytes
    @test base64encode("Julia") == "SnVsaWE="
    @test String(base64decode("SnVsaWE=")) == "Julia"
    digest = sha256("abc")
    @test length(digest) == 32
    @test bytes2hex(digest) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    @test sha1("abc") != sha1("abd")
    @test hex2bytes(bytes2hex(digest)) == digest
    @test_throws ArgumentError base64decode("AA=A")
end
