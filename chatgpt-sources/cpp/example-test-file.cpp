// Style reference for future generated GoogleTest files.
//
// The repository is currently checklist-first, so this file documents the
// desired shape for future generated tests rather than acting as a compiled
// test module.

#include <gtest/gtest.h>

#include <algorithm>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

TEST(VectorExamples, PushBackAndCheckedAccess) {
    std::vector<int> values;
    values.reserve(3);

    values.push_back(10);
    values.push_back(20);

    ASSERT_EQ(values.size(), 2);
    EXPECT_GE(values.capacity(), 3);
    EXPECT_EQ(values[0], 10);
    EXPECT_EQ(values.at(1), 20);
}

TEST(StringViewExamples, ObservesTextWithoutOwningIt) {
    std::string text = "prefix:value";
    std::string_view view{text};

    view.remove_prefix(7);

    EXPECT_EQ(view, "value");
    EXPECT_EQ(text, "prefix:value");
}

TEST(AlgorithmExamples, SortOrdersIteratorRangeInPlace) {
    std::vector<int> values{4, 1, 3, 2};
    const std::vector<int> expected{1, 2, 3, 4};

    std::sort(values.begin(), values.end());

    EXPECT_EQ(values, expected);
}

TEST(StringExamples, StoiReportsInvalidTextWithStandardException) {
    EXPECT_THROW((void)std::stoi("not-a-number"), std::invalid_argument);
}

TEST(UtilityExamples, MoveMakesOwnershipTransferVisible) {
    std::vector<std::string> source;
    source.push_back("payload");

    std::vector<std::string> target = std::move(source);

    ASSERT_EQ(target.size(), 1);
    EXPECT_EQ(target.front(), "payload");
}
