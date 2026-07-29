# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.logger-and-erb

require "assertions"
require "erb"
require "logger"
require "stringio"

A = PolyglotAssertions

template = ERB.new("<%= name %> <%= 2 + 2 %>")
template_binding = binding
template_binding.local_variable_set(:name, "Ruby")
A.equal("Ruby 4", template.result(template_binding))

output = StringIO.new
logger = Logger.new(output)
logger.level = Logger::INFO
logger.formatter = proc { |severity, _time, _program, message| "#{severity}:#{message}\n" }
logger.debug("hidden")
logger.info("visible")
logger.close

A.equal("INFO:visible\n", output.string)
A.truth(output.closed?)

A.done
