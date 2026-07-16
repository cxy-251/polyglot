"""044｜``calendar`` 周/月/年矩阵、格式化与 Gregorian 工具示例。

``calendar`` 的计算使用向前后无限延伸的 proleptic Gregorian calendar，因此部分
数值迭代器能表示 year 0 和负年份；``datetime.date`` 对象迭代器仍受 1..9999 限制。

实例 ``Calendar`` 适合局部配置周起点。模块级 first weekday 是进程全局状态，由
autouse fixture 恢复；Locale*Calendar 会临时修改全局 locale，只在子进程示范。

"""

# polyglot-covers: python.stdlib.calendar python.calendar.weekday-constants
# polyglot-covers: python.calendar.Calendar python.calendar.firstweekday
# polyglot-covers: python.calendar.iterweekdays python.calendar.itermonthdates
# polyglot-covers: python.calendar.itermonthdays python.calendar.itermonthdays2
# polyglot-covers: python.calendar.itermonthdays3 python.calendar.itermonthdays4
# polyglot-covers: python.calendar.month-calendar-matrices
# polyglot-covers: python.calendar.year-calendar-matrices
# polyglot-covers: python.calendar.TextCalendar python.calendar.HTMLCalendar
# polyglot-covers: python.calendar.locale-calendars python.calendar.locale-global-state
# polyglot-covers: python.calendar.isleap python.calendar.leapdays
# polyglot-covers: python.calendar.weekday python.calendar.monthrange
# polyglot-covers: python.calendar.localized-names python.calendar.weekheader
# polyglot-covers: python.calendar.timegm python.calendar.errors

import calendar
import subprocess
import sys
import time as time_module
from datetime import date

import pytest


@pytest.fixture(autouse=True)
def restore_module_first_weekday():
    """模块级 formatter/matrix API 共享 first weekday，测试后恢复进入时的值。"""

    original = calendar.firstweekday()
    try:
        yield
    finally:
        calendar.setfirstweekday(original)


def test_weekday_constants_and_instance_iteration_define_column_order():
    """calendar 使用 Monday=0；firstweekday 决定一周迭代和矩阵的第一列。"""

    assert (
        calendar.MONDAY,
        calendar.TUESDAY,
        calendar.WEDNESDAY,
        calendar.THURSDAY,
        calendar.FRIDAY,
        calendar.SATURDAY,
        calendar.SUNDAY,
    ) == tuple(range(7))

    monday_first = calendar.Calendar()
    sunday_first = calendar.Calendar(firstweekday=calendar.SUNDAY)

    assert monday_first.firstweekday == calendar.MONDAY
    assert list(monday_first.iterweekdays()) == [0, 1, 2, 3, 4, 5, 6]
    assert list(sunday_first.iterweekdays()) == [6, 0, 1, 2, 3, 4, 5]


def test_calendar_instance_firstweekday_can_change_without_global_mutation():
    """实例属性影响该对象，优先于修改模块级全局配置。"""

    original_global = calendar.firstweekday()
    instance = calendar.Calendar(calendar.MONDAY)

    instance.firstweekday = calendar.WEDNESDAY

    assert instance.firstweekday == calendar.WEDNESDAY
    assert list(instance.iterweekdays()) == [2, 3, 4, 5, 6, 0, 1]
    assert calendar.firstweekday() == original_global


def test_module_firstweekday_changes_global_helpers_and_is_fixture_restored():
    """setfirstweekday 影响 monthcalendar/weekheader 等模块函数，不影响既有实例。"""

    monday_instance = calendar.Calendar(calendar.MONDAY)

    assert calendar.setfirstweekday(calendar.SUNDAY) is None
    assert calendar.firstweekday() == calendar.SUNDAY
    assert list(monday_instance.iterweekdays())[0] == calendar.MONDAY

    global_matrix = calendar.monthcalendar(2024, 2)
    sunday_matrix = calendar.Calendar(calendar.SUNDAY).monthdayscalendar(2024, 2)
    assert global_matrix == sunday_matrix


def test_itermonthdates_pads_to_complete_weeks_with_neighboring_month_dates():
    """date 迭代器不会用 sentinel；目标月前后位置是可用的相邻月 date。"""

    days = list(calendar.Calendar(calendar.MONDAY).itermonthdates(2024, 2))

    assert len(days) == 35
    assert len(days) % 7 == 0
    assert days[0] == date(2024, 1, 29)
    assert days[-1] == date(2024, 3, 3)
    assert sum(day.month == 2 for day in days) == 29
    assert all(isinstance(day, date) for day in days)


def test_itermonthdays_uses_zero_for_cells_outside_the_target_month():
    """纯 day-number 版本以 0 padding；消费方必须先排除 0 再构造日期。"""

    days = list(calendar.Calendar(calendar.MONDAY).itermonthdays(2024, 2))

    assert len(days) == 35
    assert days[:4] == [0, 0, 0, 1]
    assert days[-7:] == [26, 27, 28, 29, 0, 0, 0]
    assert [day for day in days if day] == list(range(1, 30))


def test_itermonthdays2_pairs_padding_and_real_days_with_weekdays():
    """即使 day=0，weekday 仍描述该矩阵列；真实日期可按 day 筛选。"""

    entries = list(calendar.Calendar(calendar.MONDAY).itermonthdays2(2024, 2))

    assert entries[0] == (0, calendar.MONDAY)
    assert entries[3] == (1, calendar.THURSDAY)
    assert (29, calendar.THURSDAY) in entries
    assert len(entries) == 35


def test_numeric_month_iterators_support_year_zero_beyond_datetime_date_range():
    """itermonthdays3/4 返回整数 tuple，可表示 ISO 8601 的 year 0（1 BC）。"""

    calendar_data = calendar.Calendar(calendar.MONDAY)
    triples = list(calendar_data.itermonthdays3(0, 1))
    quadruples = list(calendar_data.itermonthdays4(0, 1))

    assert (0, 1, 1) in triples
    assert any((year, month, day) == (0, 1, 1) for year, month, day, _ in quadruples)
    assert all(0 <= weekday <= 6 for _, _, _, weekday in quadruples)
    assert any(year < 0 for year, _, _ in triples) or any(
        month != 1 for _, month, _ in triples
    )

    # date 对象本身不允许 year 0，所以 object iterator 不能覆盖同一范围。
    with pytest.raises(ValueError):
        list(calendar_data.itermonthdates(0, 1))


def test_month_calendar_methods_return_full_seven_cell_weeks():
    """三种矩阵共享周结构，只是 cell 分别为 date、day 或 (day, weekday)。"""

    calendar_data = calendar.Calendar(calendar.MONDAY)
    dates = calendar_data.monthdatescalendar(2024, 2)
    numbers = calendar_data.monthdayscalendar(2024, 2)
    pairs = calendar_data.monthdays2calendar(2024, 2)

    assert len(dates) == len(numbers) == len(pairs) == 5
    assert all(len(week) == 7 for week in dates + numbers + pairs)
    assert dates[0][0] == date(2024, 1, 29)
    assert numbers[0] == [0, 0, 0, 1, 2, 3, 4]
    assert pairs[0][3] == (1, calendar.THURSDAY)


def test_month_matrix_may_have_four_five_or_six_weeks():
    """UI 不应硬编码五行：Monday-first 的 2021-02 是四周，2021-05 是六周。"""

    calendar_data = calendar.Calendar(calendar.MONDAY)

    assert len(calendar_data.monthdayscalendar(2021, 2)) == 4
    assert len(calendar_data.monthdayscalendar(2024, 2)) == 5
    assert len(calendar_data.monthdayscalendar(2021, 5)) == 6


def test_year_calendar_width_groups_all_twelve_months_into_rows():
    """width 控制每行月份数，不控制每个月内部周数。"""

    calendar_data = calendar.Calendar(calendar.MONDAY)
    number_rows = calendar_data.yeardayscalendar(2024, width=4)
    pair_rows = calendar_data.yeardays2calendar(2024, width=4)
    date_rows = calendar_data.yeardatescalendar(2024, width=4)

    assert [len(row) for row in number_rows] == [4, 4, 4]
    assert [len(row) for row in pair_rows] == [4, 4, 4]
    assert [len(row) for row in date_rows] == [4, 4, 4]
    assert sum(len(row) for row in number_rows) == 12
    assert all(len(week) == 7 for row in date_rows for month in row for week in month)


def test_text_calendar_formats_month_and_year_without_full_string_snapshots():
    """月份/星期名称由 locale 决定；测试只锁定年份、日期和多行结构。"""

    formatter = calendar.TextCalendar(firstweekday=calendar.SUNDAY)
    month_text = formatter.formatmonth(2024, 2, w=2, l=1)
    year_text = formatter.formatyear(2024, m=4)

    assert isinstance(month_text, str)
    assert "2024" in month_text
    assert "29" in month_text
    assert len(month_text.splitlines()) >= 7
    assert isinstance(year_text, str)
    assert "2024" in year_text
    assert len(year_text.splitlines()) > len(month_text.splitlines())


def test_text_calendar_print_helper_writes_formatted_text_to_stdout(capsys):
    """prmonth 是有 stdout 副作用的便利方法；需要字符串时应使用 formatmonth。"""

    formatter = calendar.TextCalendar(calendar.MONDAY)

    assert formatter.prmonth(2024, 2) is None
    captured = capsys.readouterr()

    assert "2024" in captured.out
    assert "29" in captured.out
    assert captured.err == ""


def test_html_calendar_returns_tables_and_a_complete_encoded_page():
    """formatmonth/year 返回 str table；formatyearpage 返回带声明和 CSS 链接的 bytes。"""

    formatter = calendar.HTMLCalendar(calendar.MONDAY)
    month_html = formatter.formatmonth(2024, 2)
    year_html = formatter.formatyear(2024, width=4)
    page = formatter.formatyearpage(
        2024,
        width=4,
        css="project-calendar.css",
        encoding="utf-8",
    )

    assert isinstance(month_html, str)
    assert '<table border="0" cellpadding="0" cellspacing="0" class="month">' in month_html
    assert ">29<" in month_html
    assert 'class="mon"' in month_html

    assert isinstance(year_html, str)
    assert 'class="year"' in year_html
    assert year_html.count('class="month"') >= 12

    assert isinstance(page, bytes)
    decoded_page = page.decode("utf-8")
    assert "<!DOCTYPE html" in decoded_page
    assert 'charset=utf-8' in decoded_page
    assert 'href="project-calendar.css"' in decoded_page


def test_html_calendar_css_classes_are_customized_through_class_attributes():
    """继承并改 class 属性比对生成 HTML 做字符串替换更稳定。"""

    class ProjectCalendar(calendar.HTMLCalendar):
        cssclasses = [
            f"{weekday_class} project-day"
            for weekday_class in calendar.HTMLCalendar.cssclasses
        ]
        cssclasses_weekday_head = [
            f"{weekday_class} project-heading"
            for weekday_class in calendar.HTMLCalendar.cssclasses
        ]
        cssclass_month_head = "month project-month-heading"
        cssclass_month = "month project-month"

    rendered = ProjectCalendar().formatmonth(2024, 2)

    assert 'class="month project-month"' in rendered
    assert 'class="month project-month-heading"' in rendered
    assert 'class="mon project-day"' in rendered
    assert 'class="mon project-heading"' in rendered


def test_locale_calendar_is_demonstrated_in_a_process_isolated_c_locale():
    """Locale*Calendar 临时 setlocale，线程不安全；子进程隔离整个 locale 生命周期。"""

    program = r'''
import calendar
import locale

original = locale.setlocale(locale.LC_TIME)
text = calendar.LocaleTextCalendar(locale="C").formatmonth(2024, 2)
html = calendar.LocaleHTMLCalendar(locale="C").formatmonth(2024, 2)

assert "February" in text
assert "February" in html
assert locale.setlocale(locale.LC_TIME) == original
print("isolated-locale-calendar-ok")
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "isolated-locale-calendar-ok"


def test_leap_year_helpers_use_half_open_ranges_and_century_rules():
    """整百年通常不是闰年，能被 400 整除的世纪年例外；leapdays 不含 y2。"""

    assert calendar.isleap(2000)
    assert not calendar.isleap(1900)
    assert calendar.isleap(2024)
    assert not calendar.isleap(2100)
    assert calendar.isleap(0)

    assert calendar.leapdays(2000, 2001) == 1
    assert calendar.leapdays(2000, 2000) == 0
    assert calendar.leapdays(1996, 2005) == 3
    assert calendar.leapdays(2001, 2024) == 5


def test_weekday_monthrange_and_monthcalendar_share_monday_zero_numbering():
    """monthrange 返回首日 weekday 与天数；monthcalendar 再按全局周起点排成矩阵。"""

    assert calendar.weekday(2024, 2, 29) == calendar.THURSDAY
    assert calendar.monthrange(2024, 2) == (calendar.THURSDAY, 29)

    calendar.setfirstweekday(calendar.MONDAY)
    matrix = calendar.monthcalendar(2024, 2)
    assert matrix[0] == [0, 0, 0, 1, 2, 3, 4]
    assert all(len(week) == 7 for week in matrix)


def test_locale_name_sequences_keep_documented_index_shapes():
    """名称内容由当前 locale 决定；稳定契约是索引顺序、长度和 month[0] 空位。"""

    assert len(calendar.day_name) == 7
    assert len(calendar.day_abbr) == 7
    assert len(calendar.month_name) == 13
    assert len(calendar.month_abbr) == 13
    assert calendar.month_name[0] == ""
    assert calendar.month_abbr[0] == ""
    assert all(calendar.day_name[index] for index in range(7))
    assert all(calendar.month_name[index] for index in range(1, 13))

    header = calendar.weekheader(2)
    assert isinstance(header, str)
    assert header


@pytest.mark.parametrize("timestamp", [0, 1_700_000_000])
def test_timegm_is_the_utc_inverse_of_gmtime(timestamp):
    """timegm 不读取本地时区；它按 UTC/POSIX 解释 struct_time。"""

    utc_fields = time_module.gmtime(timestamp)

    assert calendar.timegm(utc_fields) == timestamp
    assert calendar.timegm((1970, 1, 1, 0, 0, 0)) == 0


def test_illegal_month_and_global_weekday_errors_are_value_errors():
    """模块级 setter 会验证 0..6；monthrange 用专门异常报告非法月份。"""

    assert issubclass(calendar.IllegalWeekdayError, ValueError)
    assert issubclass(calendar.IllegalMonthError, ValueError)

    with pytest.raises(calendar.IllegalWeekdayError):
        calendar.setfirstweekday(7)
    with pytest.raises(calendar.IllegalWeekdayError):
        calendar.setfirstweekday(-1)
    with pytest.raises(calendar.IllegalMonthError):
        calendar.monthrange(2024, 13)
