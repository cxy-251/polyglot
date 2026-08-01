# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.yaml-and-marshal-trust-boundaries

require "assertions"
require "yaml"

A = PolyglotAssertions

A.case("YAML.safe_load accepts plain data and rejects an unpermitted Ruby object tag") do
  safe_document = "---\nname: Ruby\nversion: 4\n"
  A.equal({"name" => "Ruby", "version" => 4}, YAML.safe_load(safe_document))

  tagged = "--- !ruby/object:Object {}\n"
  A.raises(Psych::DisallowedClass) { YAML.safe_load(tagged) }
end

A.case("Marshal handles trusted Ruby graphs but not every runtime object") do
  trusted = {items: [1, 2], label: "ruby"}
  dump = Marshal.dump(trusted)
  A.equal(trusted, Marshal.load(dump))
  A.raises(TypeError) { Marshal.dump(proc {}) }
  A.equal(Marshal::MAJOR_VERSION, dump.getbyte(0))
  A.equal(Marshal::MINOR_VERSION, dump.getbyte(1))
end

A.done
