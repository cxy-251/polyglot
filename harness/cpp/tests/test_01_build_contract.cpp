// polyglot-harness: cpp.cxx20-gcc-and-googletest-build-contract

#include <gtest/gtest.h>

#include <string_view>

TEST(CppHarnessContract, UsesTheLockedLanguageAndCompilerBaseline) {
    static_assert(__cplusplus == 202002L);
    static_assert(__GNUC__ == 11);
    static_assert(__GNUC_MINOR__ == 4);

    EXPECT_TRUE(std::string_view{__VERSION__}.starts_with("11.4.0"));
}
