# frozen_string_literal: true
# polyglot-covers: ruby.runtime.encoding-locale-and-timezone-boundary

require "assertions"

A = PolyglotAssertions

A.equal("UTF-8", Encoding.default_external.name)
A.equal("UTF-8", Encoding.find("locale").name)
A.equal("UTC", ENV.fetch("TZ"))
A.equal(0, Time.local(2026, 1, 1).utc_offset)

original_internal = Encoding.default_internal
begin
  Encoding.default_internal = Encoding::UTF_8
  A.same(Encoding::UTF_8, Encoding.default_internal)
  A.same(Encoding::UTF_8, "ruby".encode.encoding)
ensure
  Encoding.default_internal = original_internal
end
A.same(original_internal, Encoding.default_internal)

A.done
