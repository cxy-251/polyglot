# frozen_string_literal: true
# Harness assertion support; this file is not part of the Ruby curriculum.

module PolyglotAssertions
  class << self
    attr_reader :count

    def equal(expected, actual, message = nil)
      record(expected == actual, message || "expected #{expected.inspect}, got #{actual.inspect}")
      actual
    end

    def eql(expected, actual, message = nil)
      record(expected.eql?(actual), message || "expected eql? #{expected.inspect}, got #{actual.inspect}")
      actual
    end

    def same(expected, actual, message = nil)
      record(expected.equal?(actual), message || "expected the same object")
      actual
    end

    def truth(value, message = nil)
      record(value, message || "expected a truthy value, got #{value.inspect}")
      value
    end

    def falsey(value, message = nil)
      record(!value, message || "expected a falsey value, got #{value.inspect}")
      value
    end

    def nil_value(value, message = nil)
      record(value.nil?, message || "expected nil, got #{value.inspect}")
      value
    end

    def near(expected, actual, tolerance = 1e-12)
      difference = (expected - actual).abs
      record(difference <= tolerance, "difference #{difference} exceeds #{tolerance}")
      actual
    end

    def includes(collection, member)
      record(collection.include?(member), "#{collection.inspect} does not include #{member.inspect}")
      collection
    end

    def matches(pattern, value)
      record(pattern.match?(value), "#{value.inspect} does not match #{pattern.inspect}")
      value
    end

    def raises(exception_class, message = nil)
      begin
        yield
      rescue exception_class => error
        if message
          matched = message.is_a?(Regexp) ? message.match?(error.message) : error.message.include?(message)
          record(matched, "exception message #{error.message.inspect} does not match #{message.inspect}")
        else
          @count = count + 1
        end
        return error
      rescue Exception => error # rubocop:disable Lint/RescueException
        raise "expected #{exception_class}, got #{error.class}: #{error.message}"
      end
      raise "expected #{exception_class}, but nothing was raised"
    end

    def with_cleanup(cleanup)
      yield
    ensure
      cleanup.call
    end

    def done
      raise "no assertions were executed" if count.zero?

      puts "Ruby assertions passed: #{count}"
    end

    private

    def record(condition, message)
      raise message unless condition

      @count = count + 1
    end
  end

  @count = 0
end
