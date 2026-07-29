# frozen_string_literal: true
# polyglot-covers: ruby.objects.method-missing-and-respond-to-missing

require "assertions"

A = PolyglotAssertions

dynamic_class = Class.new do
  def method_missing(name, *arguments)
    return [name, arguments] if name.to_s.start_with?("dynamic_")

    super
  end

  def respond_to_missing?(name, include_private = false)
    name.to_s.start_with?("dynamic_") || super
  end
end

object = dynamic_class.new
A.equal([:dynamic_value, [1, 2]], object.dynamic_value(1, 2))
A.truth(object.respond_to?(:dynamic_value))
A.falsey(object.respond_to?(:ordinary_missing))
A.raises(NoMethodError) { object.ordinary_missing }
A.equal(:dynamic_value, object.method(:dynamic_value).name)

A.done
