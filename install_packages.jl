using Pkg

packages = [
    "StatsBase",
    "DataFrames",
    "Plots",
    "Combinatorics",
    "Dates",
    "ArgParse"
]

for pkg in packages
    Pkg.add(pkg)
end

