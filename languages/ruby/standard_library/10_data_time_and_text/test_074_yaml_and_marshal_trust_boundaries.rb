# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.yaml-and-marshal-trust-boundaries

require "assertions"
require "yaml"

A = PolyglotAssertions

safe_document = "---\nname: Ruby\nversion: 4\n"
A.equal({"name" => "Ruby", "version" => 4}, YAML.safe_load(safe_document))

tagged = "--- !ruby/object:Object {}\n"
A.raises(Psych::DisallowedClass) { YAML.safe_load(tagged) }

# Marshal 只对本进程生成的可信数据做 roundtrip；不可信输入不能交给 Marshal.load。
trusted = {items: [1, 2], label: "ruby"}
dump = Marshal.dump(trusted)
A.equal(trusted, Marshal.load(dump))
A.raises(TypeError) { Marshal.dump(proc {}) }
A.equal(Marshal::MAJOR_VERSION, dump.getbyte(0))
A.equal(Marshal::MINOR_VERSION, dump.getbyte(1))

A.done
