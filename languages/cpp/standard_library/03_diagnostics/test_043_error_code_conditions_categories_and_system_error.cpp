// polyglot-covers:
// - cpp.stdlib.diagnostics.error-code-value-and-category
// - cpp.stdlib.diagnostics.error-condition-portable-matching
// - cpp.stdlib.diagnostics.generic-and-system-categories
// - cpp.stdlib.diagnostics.errc-and-make-error-code
// - cpp.stdlib.diagnostics.custom-error-category
// - cpp.stdlib.diagnostics.error-category-equivalent
// - cpp.stdlib.diagnostics.system-error
// - cpp.stdlib.diagnostics.error-code-hash

#include <gtest/gtest.h>

#include <cerrno>
#include <functional>
#include <string>
#include <system_error>
#include <type_traits>
#include <unordered_map>

namespace application_errors {

enum class ServiceError {
  success = 0,
  missing_record = 1,
  permission_denied = 2,
  temporarily_unavailable = 3,
};

class ServiceCategory final : public std::error_category {
 public:
  const char* name() const noexcept override { return "polyglot.service"; }

  std::string message(int value) const override {
    switch (static_cast<ServiceError>(value)) {
      case ServiceError::success:
        return "success";
      case ServiceError::missing_record:
        return "record is missing";
      case ServiceError::permission_denied:
        return "service permission denied";
      case ServiceError::temporarily_unavailable:
        return "service temporarily unavailable";
    }
    return "unknown service error";
  }

  std::error_condition default_error_condition(int value) const noexcept override {
    switch (static_cast<ServiceError>(value)) {
      case ServiceError::permission_denied:
        return std::errc::permission_denied;
      case ServiceError::temporarily_unavailable:
        return std::errc::resource_unavailable_try_again;
      default:
        return {value, *this};
    }
  }
};

const std::error_category& service_category() {
  static const ServiceCategory category;
  return category;
}

std::error_code make_error_code(ServiceError error) {
  return {static_cast<int>(error), service_category()};
}

}  // namespace application_errors

template <>
struct std::is_error_code_enum<application_errors::ServiceError> : std::true_type {};

namespace {

using application_errors::ServiceError;

TEST(ErrorCode, ValueAndCategoryTogetherFormTheErrorIdentity) {
  const std::error_code generic{EACCES, std::generic_category()};
  const std::error_code system{EACCES, std::system_category()};

  EXPECT_EQ(generic.value(), EACCES);
  EXPECT_EQ(generic.category(), std::generic_category());
  EXPECT_FALSE(generic.message().empty());

  // 两个 code 即使整数 value 相同，只要 category 不同就不是同一错误身份。system_category
  // 解释本平台原生错误空间；generic_category 使用可移植 POSIX 风格条件空间。
  if (generic.category() != system.category()) {
    EXPECT_NE(generic, system);
  }
}

TEST(ErrorCode, DefaultObjectMeansSuccessAndClearRestoresIt) {
  std::error_code error;
  EXPECT_FALSE(error);

  error = std::make_error_code(std::errc::invalid_argument);
  EXPECT_TRUE(error);
  EXPECT_EQ(error, std::errc::invalid_argument);

  error.clear();
  EXPECT_FALSE(error);
  EXPECT_EQ(error.value(), 0);

  // error_code 的 bool 转换只检查 value != 0；约定零表示成功。自定义 category 也应保留
  // 这个约定，否则通用的 `if (error)` 控制流会误判。
}

TEST(ErrorConditions, ErrcSupportsPortableMatchingAcrossCategories) {
  const std::error_code code{EACCES, std::generic_category()};
  const std::error_condition condition = std::errc::permission_denied;

  EXPECT_EQ(code, condition);
  EXPECT_EQ(condition.category(), std::generic_category());

  // error_code 表示具体来源的错误；error_condition 表示调用者关心的可移植类别。二者比较
  // 会调用 category::equivalent，而不是只比较整数，因此可跨错误空间做语义匹配。
}

TEST(CustomCategories, EnumConvertsToAnErrorCodeThroughTheRegisteredFactory) {
  const std::error_code error = ServiceError::missing_record;

  EXPECT_EQ(error.category().name(), std::string{"polyglot.service"});
  EXPECT_EQ(error.value(), 1);
  EXPECT_EQ(error.message(), "record is missing");
  EXPECT_NE(error, std::errc::no_such_file_or_directory);

  // 特化 is_error_code_enum 后，枚举可经 ADL make_error_code 隐式转换。category 对象必须
  // 具有稳定唯一地址，通常由函数局部 static 单例提供，不能每次临时创建。
}

TEST(CustomCategories, DefaultConditionMapsDomainErrorsToPortableMeaning) {
  const std::error_code denied = ServiceError::permission_denied;
  const std::error_code unavailable = ServiceError::temporarily_unavailable;

  EXPECT_EQ(denied, std::errc::permission_denied);
  EXPECT_EQ(unavailable, std::errc::resource_unavailable_try_again);
  EXPECT_NE(std::error_code{ServiceError::missing_record},
            std::errc::no_such_file_or_directory);

  // default_error_condition 只映射语义确实等价的错误。不要因为名字相似就把领域
  // missing_record 映射成文件不存在，否则调用者可能执行错误的重试或权限处理策略。
}

TEST(SystemError, ExceptionPreservesStructuredCodeAndAddsContext) {
  const std::error_code code = ServiceError::temporarily_unavailable;
  const std::system_error error{code, "fetch profile"};

  EXPECT_EQ(error.code(), code);
  EXPECT_NE(std::string{error.what()}.find("fetch profile"), std::string::npos);
  EXPECT_NE(std::string{error.what()}.find(code.message()), std::string::npos);
  static_assert(std::is_base_of_v<std::runtime_error, std::system_error>);

  // system_error 把 error_code 与人类上下文组合成异常；机器分支应检查 code/category，
  // 不要解析 what() 文本，因为标点、语言和底层 message 都由实现或平台决定。
}

TEST(ErrorCode, HashIncludesTheCompleteErrorIdentity) {
  std::unordered_map<std::error_code, std::string> actions;
  actions.emplace(ServiceError::permission_denied, "ask for access");
  actions.emplace(ServiceError::temporarily_unavailable, "retry later");

  EXPECT_EQ(actions.at(ServiceError::permission_denied), "ask for access");
  EXPECT_EQ(actions.at(ServiceError::temporarily_unavailable), "retry later");

  // 标准提供 std::hash<error_code>，可直接用作 unordered 容器键；相等性仍由 value 与
  // category 身份共同决定，同值不同 category 必须保留成不同条目。
}

}  // namespace
