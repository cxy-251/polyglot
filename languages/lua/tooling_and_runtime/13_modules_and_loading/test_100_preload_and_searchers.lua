-- polyglot-covers: lua.modules.preload_and_searchers

local t = require("support.assertions")
local module_name = "polyglot_preloaded"
local loads = 0
local prior_preload = package.preload[module_name]
local prior_loaded = package.loaded[module_name]

package.preload[module_name] = function(name, loader_data)
    loads = loads + 1
    return {name = name, loader_data = loader_data}
end
package.loaded[module_name] = nil

local value, loader_data = require(module_name)
t.equal(value.name, module_name)
t.equal(value.loader_data, ":preload:")
t.equal(loader_data, ":preload:")
t.equal(loads, 1)
t.same(require(module_name), value)
t.equal(loads, 1)

package.preload[module_name] = prior_preload
package.loaded[module_name] = prior_loaded
t.equal(type(package.searchers), "table")
t.truth(#package.searchers >= 4)

t.done()
