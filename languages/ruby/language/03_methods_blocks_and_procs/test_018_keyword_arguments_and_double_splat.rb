# frozen_string_literal: true
# polyglot-covers: ruby.calls.keyword-arguments-and-double-splat

require "assertions"

A = PolyglotAssertions

def keyword_options(required:, optional: 2, **extra)
  [required, optional, extra]
end

A.equal([1, 2, {}], keyword_options(required: 1))
A.equal([1, 3, {flag: true}], keyword_options(required: 1, optional: 3, flag: true))
options = {required: 4, optional: 5}
A.equal([4, 5, {}], keyword_options(**options))
A.raises(ArgumentError) { keyword_options }
A.raises(ArgumentError) { keyword_options({required: 1}) }

A.done
