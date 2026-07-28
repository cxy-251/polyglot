# polyglot-covers: r.language.s4-coercion-and-setas

methods::setClass("PolyglotKelvin", slots = c(value = "numeric"))
methods::setClass("PolyglotCelsius", slots = c(value = "numeric"))
methods::setAs(
    "PolyglotCelsius",
    "PolyglotKelvin",
    function(from) methods::new("PolyglotKelvin", value = from@value + 273.15)
)

celsius <- methods::new("PolyglotCelsius", value = 20)
kelvin <- methods::as(celsius, "PolyglotKelvin")

stopifnot(
    methods::is(kelvin, "PolyglotKelvin"),
    isTRUE(all.equal(kelvin@value, 293.15)),
    methods::hasMethod("coerce", c("PolyglotCelsius", "PolyglotKelvin")),
    !methods::hasMethod("coerce", c("PolyglotKelvin", "PolyglotCelsius"))
)
