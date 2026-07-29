# polyglot-covers: r.standard-library.date-posix-time-zones-and-differences

date <- as.Date("2026-07-28")
instant <- as.POSIXct("2026-07-28 12:00:00", tz = "UTC")
later <- instant + 90
difference <- difftime(later, instant, units = "secs")

stopifnot(
    identical(format(date, "%Y-%m-%d"), "2026-07-28"),
    identical(format(instant, "%H:%M", tz = "UTC"), "12:00"),
    identical(typeof(date), "double"),
    inherits(date, "Date"),
    inherits(instant, c("POSIXct", "POSIXt")),
    identical(attr(instant, "tzone"), "UTC"),
    inherits(difference, "difftime"),
    identical(as.numeric(difference, units = "secs"), 90)
)

# Date 计公历日，POSIXct 计时间线秒，difftime 携带单位；格式化时区不改变底层 instant。
