# 共同问题：数值精度、版本和信任边界怎样限制传输格式。
# 输入：大整数、浮点、Marshal header、JSON 非数值和不可信 YAML tag；观察：保真度、拒绝策略及版本。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/test_074_yaml_and_marshal_trust_boundaries.rb

require "assertions"
require "json"
require "yaml"

A = PolyglotAssertions

large = 2**100
A.equal(large, JSON.parse(JSON.generate(large)))
A.near(Math::PI, JSON.parse(JSON.generate(Math::PI)))
A.raises(JSON::GeneratorError) { JSON.generate(Float::NAN) }

dump = Marshal.dump({value: large})
A.equal(Marshal::MAJOR_VERSION, dump.getbyte(0))
A.equal(Marshal::MINOR_VERSION, dump.getbyte(1))
A.equal({value: large}, Marshal.load(dump))

unsafe_yaml = "--- !ruby/object:Object {}\n"
A.raises(Psych::DisallowedClass) { YAML.safe_load(unsafe_yaml, permitted_classes: []) }

A.done
