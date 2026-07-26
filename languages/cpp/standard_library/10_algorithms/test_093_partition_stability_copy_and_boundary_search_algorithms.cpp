// polyglot-covers:
// - cpp.stdlib.algorithms.is-partitioned-predicate-boundary
// - cpp.stdlib.algorithms.partition-membership-and-unspecified-relative-order
// - cpp.stdlib.algorithms.ranges-partition-returned-tail-subrange
// - cpp.stdlib.algorithms.stable-partition-relative-order
// - cpp.stdlib.algorithms.partition-copy-two-stable-output-sequences
// - cpp.stdlib.algorithms.ranges-partition-copy-result-object
// - cpp.stdlib.algorithms.partition-point-precondition-and-return
// - cpp.stdlib.algorithms.partition-point-projection
// - cpp.stdlib.algorithms.repeated-stable-partition-multigroup-workflow

#include <gtest/gtest.h>

#include <algorithm>
#include <array>
#include <iterator>
#include <ranges>
#include <string>
#include <vector>

namespace {

bool IsEven(int value) {
  return value % 2 == 0;
}

TEST(IsPartitioned, ItChecksForASingleTrueToFalseBoundary) {
  const std::array<int, 6> partitioned{2, 4, 6, 1, 3, 5};
  const std::array<int, 5> interleaved{2, 4, 1, 6, 3};

  EXPECT_TRUE(std::ranges::is_partitioned(partitioned, IsEven));
  EXPECT_FALSE(std::ranges::is_partitioned(interleaved, IsEven));

  // “已分区”只要求所有 true 元素出现在所有 false 元素之前，不要求两侧排序。
  // 一旦进入 false 区域又看到 true，is_partitioned 就返回 false。
}

TEST(IsPartitioned, EmptyAndOneSidedRangesAreAlreadyPartitioned) {
  const std::vector<int> empty;
  const std::vector<int> all_true{2, 4, 6};
  const std::vector<int> all_false{1, 3, 5};

  EXPECT_TRUE(std::ranges::is_partitioned(empty, IsEven));
  EXPECT_TRUE(std::ranges::is_partitioned(all_true, IsEven));
  EXPECT_TRUE(std::ranges::is_partitioned(all_false, IsEven));

  // 边界可以位于 begin 或 end；“两边都必须非空”不是 partition 的语义要求。
}

TEST(Partition, ItGroupsByMembershipButDoesNotPromiseRelativeOrder) {
  std::vector<int> values{1, 2, 3, 4, 5, 6};

  auto boundary = std::partition(values.begin(), values.end(), IsEven);

  EXPECT_TRUE(std::all_of(values.begin(), boundary, IsEven));
  EXPECT_TRUE(std::none_of(boundary, values.end(), IsEven));
  EXPECT_EQ(std::distance(values.begin(), boundary), 3);

  // partition 保证成员归属，不保证 true 区或 false 区内部相对顺序。测试不应锁定某个
  // 实现恰好产生的排列；需要稳定性时用 stable_partition。
}

TEST(RangesPartition, ReturnedSubrangeStartsAtThePartitionBoundary) {
  std::array<int, 7> values{7, 2, 4, 9, 6, 1, 8};

  auto false_tail = std::ranges::partition(values, IsEven);

  EXPECT_EQ(false_tail.end(), values.end());
  EXPECT_EQ(std::distance(values.begin(), false_tail.begin()), 4);
  EXPECT_TRUE(std::ranges::all_of(
      std::ranges::subrange(values.begin(), false_tail.begin()), IsEven));
  EXPECT_TRUE(std::ranges::none_of(false_tail, IsEven));

  // ranges::partition 返回 `[partition_point,last)`，而不是只返回 boundary。对临时非
  // borrowed range 调用时，返回类型会退化为 dangling，防止保存失效 iterator。
}

TEST(StablePartition, ItPreservesTheInputOrderInsideBothGroups) {
  struct Event {
    int sequence;
    bool urgent;
  };
  std::vector<Event> events{
      {1, false}, {2, true}, {3, false}, {4, true}, {5, true}, {6, false}};

  auto normal_tail = std::ranges::stable_partition(events, &Event::urgent);

  EXPECT_EQ(normal_tail.begin(), events.begin() + 3);
  EXPECT_EQ(events[0].sequence, 2);
  EXPECT_EQ(events[1].sequence, 4);
  EXPECT_EQ(events[2].sequence, 5);
  EXPECT_EQ(events[3].sequence, 1);
  EXPECT_EQ(events[4].sequence, 3);
  EXPECT_EQ(events[5].sequence, 6);

  // stable_partition 对 true 组与 false 组分别保持原相对顺序。projection 可以直接
  // 选择 bool 成员；稳定性可能需要额外内存，但结果语义不因实现策略而变化。
}

TEST(PartitionCopy, ItBuildsTwoOutputsWithoutChangingTheSource) {
  const std::vector<int> source{5, 2, 7, 4, 1, 6};
  std::vector<int> evens;
  std::vector<int> odds;

  std::partition_copy(
      source.begin(),
      source.end(),
      std::back_inserter(evens),
      std::back_inserter(odds),
      IsEven);

  EXPECT_EQ(evens, (std::vector<int>{2, 4, 6}));
  EXPECT_EQ(odds, (std::vector<int>{5, 7, 1}));
  EXPECT_EQ(source, (std::vector<int>{5, 2, 7, 4, 1, 6}));

  // 输入按顺序扫描一次，因此两个输出各自保持源中的相对顺序。两个输出范围不得相互
  // 重叠，也不得以会覆盖未读输入的方式与输入重叠。
}

TEST(RangesPartitionCopy, ResultReportsInputAndBothOutputEnds) {
  struct Record {
    std::string name;
    int score;
  };
  const std::array<Record, 4> records{{
      {"A", 80},
      {"B", 55},
      {"C", 90},
      {"D", 40},
  }};
  std::vector<Record> passed;
  std::vector<Record> failed;

  auto result = std::ranges::partition_copy(
      records,
      std::back_inserter(passed),
      std::back_inserter(failed),
      [](int score) {
        return score >= 60;
      },
      &Record::score);

  EXPECT_EQ(result.in, records.end());
  *result.out1 = Record{"E", 100};
  *result.out2 = Record{"F", 0};
  ASSERT_EQ(passed.size(), 3U);
  ASSERT_EQ(failed.size(), 3U);
  EXPECT_EQ(passed[0].name, "A");
  EXPECT_EQ(passed[1].name, "C");
  EXPECT_EQ(failed[0].name, "B");
  EXPECT_EQ(failed[1].name, "D");

  // in_out_out_result 让两个输出都能从各自尾部继续写；projection 在 predicate 前执行，
  // 被复制的仍是完整 Record，而不是投影出的 score。
}

TEST(PartitionPoint, ItFindsTheTrueFalseBoundaryInAnAlreadyPartitionedRange) {
  const std::array<int, 7> values{2, 4, 6, 8, 1, 3, 5};

  auto boundary = std::partition_point(values.begin(), values.end(), IsEven);

  EXPECT_EQ(boundary, values.begin() + 4);
  EXPECT_EQ(*boundary, 1);

  // partition_point 的前置条件是输入已经按同一个谓词分区；它不是“从任意序列找第一
  // 个 false”。违反前置条件时不能依赖返回位置，应先 is_partitioned 或先 partition。
}

TEST(PartitionPoint, BoundaryCanBeAtEitherEnd) {
  const std::array<int, 3> all_true{2, 4, 6};
  const std::array<int, 3> all_false{1, 3, 5};

  EXPECT_EQ(std::ranges::partition_point(all_true, IsEven), all_true.end());
  EXPECT_EQ(std::ranges::partition_point(all_false, IsEven), all_false.begin());

  // 随机访问范围可用对数次谓词判断定位；forward iterator 虽也只需对数次判断，但推进
  // iterator 的总次数仍可能是线性的，不能把它等同于随机访问的整体复杂度。
}

TEST(PartitionPoint, ProjectionSupportsSearchingARecordBoundary) {
  struct Job {
    int priority;
    std::string name;
  };
  const std::vector<Job> jobs{{9, "critical"}, {7, "high"}, {4, "normal"}, {1, "low"}};

  auto first_normal = std::ranges::partition_point(
      jobs,
      [](int priority) {
        return priority >= 5;
      },
      &Job::priority);

  ASSERT_NE(first_normal, jobs.end());
  EXPECT_EQ(first_normal->name, "normal");

  // projection 使“按 priority 已分区”的结构可直接查询，不必先构造 priority 临时数组。
}

TEST(StablePartitionWorkflow, RepeatedBoundariesCanBuildSeveralStableGroups) {
  struct Task {
    int id;
    int severity;
  };
  std::vector<Task> tasks{{1, 1}, {2, 3}, {3, 2}, {4, 3}, {5, 1}, {6, 2}};

  auto after_critical = std::stable_partition(
      tasks.begin(), tasks.end(), [](const Task& task) {
        return task.severity == 3;
      });
  auto after_normal = std::stable_partition(
      after_critical, tasks.end(), [](const Task& task) {
        return task.severity == 2;
      });

  EXPECT_EQ(std::vector<int>({tasks[0].id, tasks[1].id}),
            (std::vector<int>{2, 4}));
  EXPECT_EQ(std::vector<int>({tasks[2].id, tasks[3].id}),
            (std::vector<int>{3, 6}));
  EXPECT_EQ(std::vector<int>({tasks[4].id, tasks[5].id}),
            (std::vector<int>{1, 5}));
  EXPECT_EQ(after_critical, tasks.begin() + 2);
  EXPECT_EQ(after_normal, tasks.begin() + 4);

  // 在剩余尾部继续稳定分区，可以建立多个稳定组；保存的 boundary 只要后续算法不改变
  // 容器大小或触发重分配就仍有效。
}

}  // namespace
