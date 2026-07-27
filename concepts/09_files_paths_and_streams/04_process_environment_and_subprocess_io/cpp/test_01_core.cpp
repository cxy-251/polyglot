// 进程环境与子进程输入输出。
// 共同问题：环境、工作目录和参数属于谁；如何向子进程传入数据并取得输出与退出状态；
// 哪些能力属于语言标准库，哪些依赖运行时或操作系统。
//
// polyglot-family: files_paths_and_streams
// polyglot-concept: process_environment_and_subprocess_io
// polyglot-related: languages/cpp/standard_library/14_input_output/
// polyglot-related+: test_134_c_stdio_files_buffers_formatted_io_and_inttypes.cpp

#include <gtest/gtest.h>

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <string>

namespace {

TEST(ProcessEnvironmentConcept, GetenvBorrowsProcessEnvironmentStorage) {
  const char* path = std::getenv("PATH");

  ASSERT_NE(path, nullptr);
  EXPECT_FALSE(std::string{path}.empty());

  // 指针由运行时拥有；后续环境修改可能使其失效，且标准库没有环境映射快照类型。
}

TEST(ProcessEnvironmentConcept, CurrentPathIsProcessGlobalState) {
  const std::filesystem::path original = std::filesystem::current_path();
  const std::filesystem::path temporary = std::filesystem::temp_directory_path();

  std::filesystem::current_path(temporary);
  EXPECT_EQ(std::filesystem::current_path(), temporary);
  std::filesystem::current_path(original);
}

TEST(ProcessEnvironmentConcept, StandardStreamsCanBeRedirectedAtBufferBoundary) {
  std::istringstream input{"hello"};
  std::ostringstream output;
  std::streambuf* old_input = std::cin.rdbuf(input.rdbuf());
  std::streambuf* old_output = std::cout.rdbuf(output.rdbuf());
  std::string value;

  std::cin >> value;
  std::cout << value;
  std::cin.rdbuf(old_input);
  std::cout.rdbuf(old_output);

  EXPECT_EQ(output.str(), "hello");

  // std::system 只把字符串交给实现定义的命令处理器；它不提供参数数组、stdin/stdout 管道或
  // 可移植的退出状态解码，因此不执行外部命令来伪装成 Python subprocess 或 Node child_process。
}

}  // namespace
