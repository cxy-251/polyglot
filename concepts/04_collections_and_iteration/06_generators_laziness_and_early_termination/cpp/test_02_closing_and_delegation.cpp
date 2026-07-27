// 提前终止的关闭协议与委托。
// 共同问题：消费方提前停止时是否通知生产方；清理如何穿过委托层；
// 关闭失败如何传播给消费方。
//
// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/cpp/standard_library/09_ranges/
// polyglot-related+: test_085_take_drop_take_while_and_drop_while_prefix_views.cpp
// polyglot-related: languages/cpp/language/test_021_coroutines_promise_awaiter_and_generator.cpp

#include <gtest/gtest.h>

#include <string>
#include <vector>

namespace {

class ClosableRange {
 public:
  explicit ClosableRange(std::vector<std::string>& events) : events_(events) {}

  auto begin() {
    events_.push_back("begin");
    return values_.begin();
  }

  auto end() {
    return values_.end();
  }

  void close() {
    events_.push_back("close");
  }

 private:
  std::vector<std::string>& events_;
  std::vector<int> values_{1, 2};
};

TEST(EarlyTerminationConcept, RangeForBreakDoesNotCallAnAdHocCloseMember) {
  std::vector<std::string> events;
  ClosableRange values{events};

  for (int value : values) {
    EXPECT_EQ(value, 1);
    break;
  }

  EXPECT_EQ(events, (std::vector<std::string>{"begin"}));

  values.close();
  EXPECT_EQ(events, (std::vector<std::string>{"begin", "close"}));

  // range-for 只展开 begin/end、比较、解引用和递增，没有 Python generator.close 或
  // JavaScript IteratorClose。需要提前清理的 range 必须用 RAII 生命周期或显式协议。
}

}  // namespace
