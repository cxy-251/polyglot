# polyglot-covers: r.standard-library.date-time-zones-and-differences

date <- as.Date("2026-07-28")
instant <- as.POSIXct("2026-07-28 12:00:00", tz = "UTC")
later <- instant + 90
difference <- difftime(later, instant, units = "secs")

stopifnot(
    identical(format(date, "%Y-%m-%d"), "2026-07-28"),
    identical(format(instant, "%H:%M", tz = "UTC"), "12:00"),
    inherits(instant, c("POSIXct", "POSIXt")),
    inherits(difference, "difftime"),
    identical(as.numeric(difference, units = "secs"), 90)
)
