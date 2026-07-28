args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) {
    stop("run_test.R expects exactly one test file", call. = FALSE)
}

locale_categories <- c(
    "LC_COLLATE",
    "LC_CTYPE",
    "LC_MONETARY",
    "LC_NUMERIC",
    "LC_TIME"
)

connection_ids <- function() {
    connections <- showConnections(all = TRUE)
    if (is.null(connections)) character() else rownames(connections)
}

device_ids <- function() {
    devices <- grDevices::dev.list()
    if (is.null(devices)) integer() else unname(devices)
}

snapshot_state <- function() {
    has_random_seed <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    list(
        options = options(),
        environment = Sys.getenv(),
        working_directory = getwd(),
        locale = setNames(vapply(locale_categories, Sys.getlocale, ""), locale_categories),
        library_paths = .libPaths(),
        search_path = search(),
        connections = connection_ids(),
        output_sinks = sink.number(type = "output"),
        message_sinks = sink.number(type = "message"),
        devices = device_ids(),
        has_random_seed = has_random_seed,
        random_seed = if (has_random_seed) get(".Random.seed", envir = .GlobalEnv) else NULL
    )
}

restore_state <- function(state) {
    while (sink.number(type = "message") > state$message_sinks) {
        sink(type = "message")
    }
    while (sink.number(type = "output") > state$output_sinks) {
        sink(type = "output")
    }

    for (device in setdiff(device_ids(), state$devices)) {
        try(grDevices::dev.off(device), silent = TRUE)
    }
    for (connection in setdiff(connection_ids(), state$connections)) {
        try(close(getConnection(as.integer(connection))), silent = TRUE)
    }
    for (entry in rev(setdiff(search(), state$search_path))) {
        try(detach(entry, character.only = TRUE, unload = FALSE), silent = TRUE)
    }

    .libPaths(state$library_paths)
    setwd(state$working_directory)
    for (category in names(state$locale)) {
        suppressWarnings(Sys.setlocale(category, state$locale[[category]]))
    }

    current_environment <- Sys.getenv()
    extra_environment <- setdiff(names(current_environment), names(state$environment))
    if (length(extra_environment)) {
        Sys.unsetenv(extra_environment)
    }
    do.call(Sys.setenv, as.list(state$environment))

    current_options <- options()
    extra_options <- setdiff(names(current_options), names(state$options))
    if (length(extra_options)) {
        do.call(options, setNames(rep(list(NULL), length(extra_options)), extra_options))
    }
    do.call(options, state$options)

    if (state$has_random_seed) {
        assign(".Random.seed", state$random_seed, envir = .GlobalEnv)
    } else if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
        rm(".Random.seed", envir = .GlobalEnv)
    }
}

state_differences <- function(before, after) {
    checks <- c(
        options = identical(before$options, after$options),
        environment = identical(before$environment, after$environment),
        working_directory = identical(before$working_directory, after$working_directory),
        locale = identical(before$locale, after$locale),
        library_paths = identical(before$library_paths, after$library_paths),
        search_path = identical(before$search_path, after$search_path),
        connections = identical(before$connections, after$connections),
        output_sinks = identical(before$output_sinks, after$output_sinks),
        message_sinks = identical(before$message_sinks, after$message_sinks),
        devices = identical(before$devices, after$devices),
        random_seed = identical(
            list(before$has_random_seed, before$random_seed),
            list(after$has_random_seed, after$random_seed)
        )
    )
    names(checks)[!checks]
}

run_test <- function(path) {
    before <- snapshot_state()
    test_environment <- new.env(parent = globalenv())
    test_error <- NULL

    tryCatch(
        sys.source(path, envir = test_environment, keep.source = TRUE),
        error = function(condition) {
            test_error <<- condition
        }
    )

    after <- snapshot_state()
    differences <- state_differences(before, after)
    restore_state(before)

    if (!is.null(test_error)) {
        stop(test_error)
    }
    if (length(differences)) {
        stop(
            sprintf("test leaked process state: %s", paste(differences, collapse = ", ")),
            call. = FALSE
        )
    }
    cat(sprintf("R test passed: %s\n", path))
}

run_test(normalizePath(args[[1L]], mustWork = TRUE))
