# 共同问题：序列化和 clone 会复制什么，是否保留共享引用。
# 输入：嵌套 Hash、共享子对象、Marshal、JSON 和 dup；观察：身份丢失、alias 保留策略及类型变化。
# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/ruby/standard_library/10_data_time_and_text/test_074_yaml_and_marshal_trust_boundaries.rb

require "assertions"
require "json"

A = PolyglotAssertions

shared = ["ruby"]
document = {left: shared, right: shared}
restored = Marshal.load(Marshal.dump(document))
A.equal(document, restored)
A.falsey(document.equal?(restored))
A.same(restored[:left], restored[:right])

json = JSON.parse(JSON.generate(document))
A.equal(["left", "right"], json.keys)
A.equal(["ruby"], json.fetch("left"))
A.falsey(json.fetch("left").equal?(json.fetch("right")))

shallow = document.dup
A.same(document[:left], shallow[:left])

A.done
