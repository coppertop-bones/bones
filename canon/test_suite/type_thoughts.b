
// class is structure, type is role


// <:int> compiler / runtime coerces and causes the answer to be labeled with the type
a: 1.0 + 1.0 <:int>   // is sugar for
1.0+1.0 <:int> :a     // note type may not change after that point though subtypes can be assigned e.g.
a: 1 <:row>

// utilities
assert: {[same:bool]
    if[!same; `AssertionError throw]
}
assert: {[expected, actual]
    if[expected != actual; `AssertionError throw]
}

// OPEN: maybe this syntax could be convenient (types with no name)?
// ifTrue:{[:bool, :expressionList]
//     if[x;^y]
// }


// so {[ is start of parameter list, ] is end of list, } is end of function (captured in parsing not lexing)


