# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.json-and-csv-roundtrips

require "assertions"
require "csv"
require "json"

A = PolyglotAssertions

A.case("JSON round-trips its data model and rejects incomplete syntax") do
  document = {"name" => "Ruby", "version" => 4, "stable" => true}
  encoded = JSON.generate(document)
  A.equal(document, JSON.parse(encoded))
  A.raises(JSON::ParserError) { JSON.parse("{") }
end

A.case("CSV headers address fields while unconverted field data remains text") do
  csv = CSV.generate do |output|
    output << %w[name version]
    output << ["Ruby", 4]
  end
  rows = CSV.parse(csv, headers: true)
  A.equal("Ruby", rows.first["name"])
  A.equal("4", rows.first["version"])
  A.equal(%w[name version], rows.headers)
end

A.done
