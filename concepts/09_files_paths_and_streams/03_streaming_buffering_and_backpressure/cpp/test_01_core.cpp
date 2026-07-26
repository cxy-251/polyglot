// 流、缓冲与背压。
// 共同问题：文本与字节流如何区分；游标和刷新何时生效；生产者如何知道消费者暂时跟不上；
// 同步流与事件驱动流是否采用同一种背压协议。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: streaming_buffering_and_backpressure
// polyglot-related: languages/cpp/standard_library/14_input_output/
// polyglot-related+: test_126_ios_base_state_format_storage_callbacks_and_positions.cpp

#include <gtest/gtest.h>

#include <array>
#include <sstream>
#include <string>

namespace {

TEST(StreamConcept, StringStreamsFormatTypedValuesIntoCharacters) {
  std::ostringstream output;
  output << 42 << ' ' << true;

  EXPECT_EQ(output.str(), "42 1");
}

TEST(StreamConcept, SeekChangesTheReadCursor) {
  std::istringstream input{"abcdef"};
  input.seekg(2);
  std::array<char, 3> buffer{};
  input.read(buffer.data(), 2);
  const std::string result{buffer.data(), 2};

  EXPECT_EQ(result, "cd");
  EXPECT_EQ(input.gcount(), 2);
}

TEST(StreamConcept, FlushRequestsEmissionFromTheStreamBuffer) {
  std::ostringstream output;
  output << "value" << std::flush;

  EXPECT_TRUE(output.good());
  EXPECT_EQ(output.str(), "value");
}

TEST(StreamConcept, StandardIostreamHasNoAsynchronousDrainProtocol) {
  // operator<<、write 和 streambuf 的同步调用通过状态位、异常或写入计数报告结果；
  // C++20 标准库没有与 Node.js highWaterMark/drain 等价的事件驱动背压接口。
  SUCCEED();
}

}  // namespace
