# polyglot-covers: r.language.date-posixct-and-difftime-storage

date <- as.Date("1970-01-02")
instant <- as.POSIXct("1970-01-01 00:00:01", tz = "UTC")
duration <- difftime(as.POSIXct("1970-01-01 00:01:00", tz = "UTC"), instant, units = "secs")

stopifnot(
    identical(typeof(date), "double"),
    identical(unclass(date), 1),
    inherits(instant, "POSIXct"),
    identical(as.numeric(instant), 1),
    inherits(duration, "difftime"),
    identical(as.numeric(duration, units = "secs"), 59)
)
