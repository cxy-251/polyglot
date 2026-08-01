# frozen_string_literal: true
# Harness behavior-case and assertion support; this file is not part of the Ruby curriculum.

require "json"

module PolyglotAssertions
  class AssertionFailure < StandardError
    attr_reader :assertion, :expected, :actual, :original

    def initialize(assertion:, expected:, actual:, message:, original: nil)
      @assertion = assertion
      @expected = expected
      @actual = actual
      @original = original
      super(message)
    end
  end

  class SuiteFailure < StandardError; end

  Failure = Data.define(:case_name, :error)

  class << self
    attr_reader :count, :case_count, :skipped_count

    def case(name)
      validate_case_name(name)
      raise ArgumentError, "nested behavior cases are not supported" if @current_case

      @case_names << name
      @case_count += 1
      @current_case = name
      assertion_start = count
      begin
        yield
        @passed_count += 1
        puts "PASS #{test_file} :: #{name} (#{count - assertion_start} assertions)"
      # A test case may intentionally exercise ScriptError/SystemExit boundaries.
      rescue Exception => error # rubocop:disable Lint/RescueException
        @failures << Failure.new(name, error)
        report_failure(name, error)
      ensure
        @current_case = nil
      end
    end

    def skip(name, reason)
      validate_case_name(name)
      raise ArgumentError, "skip cannot be declared inside a behavior case" if @current_case
      raise ArgumentError, "skip reason must not be empty" if reason.to_s.empty?

      @case_names << name
      @case_count += 1
      @skipped_count += 1
      puts "SKIP #{test_file} :: #{name} (#{reason})"
    end

    def equal(expected, actual, message = nil)
      record(
        expected == actual,
        assertion: "equal",
        expected:,
        actual:,
        message: message || "expected #{expected.inspect}, got #{actual.inspect}"
      )
      actual
    end

    def eql(expected, actual, message = nil)
      record(
        expected.eql?(actual),
        assertion: "eql",
        expected:,
        actual:,
        message: message || "expected eql? #{expected.inspect}, got #{actual.inspect}"
      )
      actual
    end

    def same(expected, actual, message = nil)
      record(
        expected.equal?(actual),
        assertion: "same object",
        expected: "object_id=#{expected.object_id}",
        actual: "object_id=#{actual.object_id}",
        message: message || "expected the same object"
      )
      actual
    end

    def truth(value, message = nil)
      record(
        value,
        assertion: "truth",
        expected: "truthy value",
        actual: value,
        message: message || "expected a truthy value, got #{value.inspect}"
      )
      value
    end

    def falsey(value, message = nil)
      record(
        !value,
        assertion: "falsey",
        expected: "false or nil",
        actual: value,
        message: message || "expected a falsey value, got #{value.inspect}"
      )
      value
    end

    def nil_value(value, message = nil)
      record(
        value.nil?,
        assertion: "nil",
        expected: nil,
        actual: value,
        message: message || "expected nil, got #{value.inspect}"
      )
      value
    end

    def near(expected, actual, tolerance = 1e-12)
      difference = (expected - actual).abs
      record(
        difference <= tolerance,
        assertion: "near",
        expected: "#{expected.inspect} ± #{tolerance.inspect}",
        actual:,
        message: "difference #{difference} exceeds #{tolerance}"
      )
      actual
    end

    def includes(collection, member)
      record(
        collection.include?(member),
        assertion: "includes",
        expected: member,
        actual: collection,
        message: "#{collection.inspect} does not include #{member.inspect}"
      )
      collection
    end

    def matches(pattern, value)
      record(
        pattern.match?(value),
        assertion: "matches",
        expected: pattern,
        actual: value,
        message: "#{value.inspect} does not match #{pattern.inspect}"
      )
      value
    end

    def raises(exception_class, message = nil)
      error = begin
        yield
        nil
      rescue exception_class => caught
        caught
      # `raises` must also compare non-StandardError classes such as SyntaxError and SystemExit.
      rescue Exception => caught # rubocop:disable Lint/RescueException
        caught
      end

      unless error
        record(
          false,
          assertion: "raises",
          expected: exception_class,
          actual: "nothing raised",
          message: "expected #{exception_class}, but nothing was raised"
        )
      end
      unless error.is_a?(exception_class)
        record(
          false,
          assertion: "raises",
          expected: exception_class,
          actual: error.class,
          message: "expected #{exception_class}, got #{error.class}: #{error.message}",
          original: error
        )
      end

      if message
        matched = message.is_a?(Regexp) ? message.match?(error.message) : error.message.include?(message)
        record(
          matched,
          assertion: "raises message",
          expected: message,
          actual: error.message,
          message: "exception message #{error.message.inspect} does not match #{message.inspect}",
          original: error
        )
      else
        record(
          true,
          assertion: "raises",
          expected: exception_class,
          actual: error.class,
          message: "expected #{exception_class}"
        )
      end
      error
    end

    def with_cleanup(cleanup)
      yield
    ensure
      cleanup.call
    end

    def done
      if count.zero? && skipped_count != case_count
        raise SuiteFailure, "no assertions were executed"
      end
      if case_count.zero? && ENV["POLYGLOT_REQUIRE_NAMED_CASES"] == "1"
        raise SuiteFailure, "no named behavior cases were executed"
      end

      emit_metrics
      if case_count.zero?
        puts "Ruby legacy assertions passed: #{count}"
      else
        puts(
          "Ruby behavior cases: #{@passed_count} passed, #{@failures.length} failed, " \
          "#{skipped_count} skipped; #{count} assertions"
        )
      end
      raise SuiteFailure, "#{@failures.length} behavior case(s) failed" unless @failures.empty?
    end

    private

    def validate_case_name(name)
      raise ArgumentError, "case name must be a non-empty String" unless name.is_a?(String) && !name.empty?
      raise ArgumentError, "duplicate behavior case name: #{name}" if @case_names.include?(name)
    end

    def record(condition, assertion:, expected:, actual:, message:, original: nil)
      @count += 1
      return if condition

      raise AssertionFailure.new(assertion:, expected:, actual:, message:, original:)
    end

    def report_failure(name, error)
      assertion = error.is_a?(AssertionFailure) ? error.assertion : "case completes without exception"
      expected = error.is_a?(AssertionFailure) ? error.expected : "no exception"
      actual = error.is_a?(AssertionFailure) ? error.actual : "#{error.class}: #{error.message}"
      original = error.is_a?(AssertionFailure) && error.original ? error.original : error
      location = original.backtrace&.first || "unavailable"

      puts "FAIL #{test_file} :: #{name}"
      puts "  assertion: #{assertion}"
      puts "  expected: #{expected.inspect}"
      puts "  actual: #{actual.inspect}"
      puts "  original: #{original.class}: #{original.message}"
      puts "  at: #{location}"
    end

    def emit_metrics
      metrics = {
        language: "ruby",
        layer: ENV.fetch("POLYGLOT_TEST_LAYER", "unknown"),
        file: test_file,
        files: 1,
        cases: case_count,
        assertions: count,
        skipped: skipped_count,
        failed: @failures.length
      }
      puts "POLYGLOT_METRICS #{JSON.generate(metrics)}"
    end

    def test_file
      $PROGRAM_NAME
    end
  end

  @count = 0
  @case_count = 0
  @passed_count = 0
  @skipped_count = 0
  @case_names = []
  @failures = []
  @current_case = nil
end
