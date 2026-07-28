-- polyglot-covers: lua.math.extrema_angles_and_logs

local t = require("support.assertions")

t.equal(math.min(4, -2, 7), -2)
t.equal(math.max(4, -2, 7), 7)
t.near(math.deg(math.pi), 180, 1e-12)
t.near(math.rad(180), math.pi, 1e-12)
t.near(math.log(8, 2), 3, 1e-12)
t.near(math.exp(1), math.exp(1.0), 0)
t.near(math.atan(1, 1), math.pi / 4, 1e-15)

t.done()
