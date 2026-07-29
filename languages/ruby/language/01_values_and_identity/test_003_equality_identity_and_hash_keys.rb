# frozen_string_literal: true
# polyglot-covers: ruby.values.equality-identity-and-case-equality

require "assertions"

A = PolyglotAssertions

left = "ruby"
right = +"ruby"
A.truth(left == right)
A.truth(left.eql?(right))
A.falsey(left.equal?(right))
A.truth(1 == 1.0)
A.falsey(1.eql?(1.0))

# Hash 以 eql? 与 hash 组成键协议，不采用数值 == 的宽松比较。
mapping = {1 => :integer, 1.0 => :float, left => :text}
A.equal(3, mapping.size)
A.equal(:text, mapping[right])
A.equal(left.hash, right.hash)

# === 是 case 的协议入口，各接收者可定义不同的成员或匹配语义。
A.truth((1..5) === 3)
A.truth(Integer === 42)
A.truth(/uby/ === "ruby")
A.equal(:integer, case 42
                  when String then :string
                  when Integer then :integer
                  end)

A.done
