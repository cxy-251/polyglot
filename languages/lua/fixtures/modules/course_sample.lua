local module = {
    answer = 42,
    loaded_as = ...,
}

function module.double(value)
    return value * 2
end

return module
