# frozen_string_literal: true
# polyglot-covers: ruby.objects.method-visibility

require "assertions"

A = PolyglotAssertions

dynamic_class = Class.new do
  def public_value
    private_value
  end

  def method_missing(name, *arguments)
    return [name, arguments] if name.to_s.start_with?("dynamic_")

    super
  end

  def respond_to_missing?(name, include_private = false)
    name.to_s.start_with?("dynamic_") || super
  end

  private

  def private_value
    :private
  end
end

object = dynamic_class.new
A.equal(:private, object.public_value)
A.raises(NoMethodError) { object.private_value }
A.equal(:private, object.send(:private_value))
A.raises(NoMethodError) { object.public_send(:private_value) }
A.falsey(object.respond_to?(:private_value))
A.truth(object.respond_to?(:private_value, true))

A.equal([:dynamic_value, [1, 2]], object.dynamic_value(1, 2))
A.truth(object.respond_to?(:dynamic_value))
A.equal(:dynamic_value, object.method(:dynamic_value).name)
A.raises(NoMethodError) { object.ordinary_missing }

A.done
