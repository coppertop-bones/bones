### ACCESSING

PMF & L
```
like: {A: 0.5, B: 1.0, C: 0.0, hyp:`A} <:L>

v1: like atField sym
v1 typeOf == <:sym + float>

v2: like restrictedAtField(,,`A`B`C) sym
v2 typeOf == <:float>

v3: like.hyp
v3 typeOf == <:sym>

v4: like at `hyp
v4 typeOf == <:sym>
```

Do we allow?

```
v1: like sym    // object object apply
v4: like `hyp   // object object apply
```

disadvantages are we have to have magic methods, and it's one more syntactic rule to understand and implement
advantage is we can be a little more terse


```
modelState: ({V:30, C:10, tag:`J1}, {V:20, C:20, tag:`J2})

jarLike: {[jarStates, data:sym] <:L> 
    jarStates collect {(jarState.tag, jarState restrictedAtField(,,`V`C)) sym} to <:L>
}

{J1:0.5, J2:0.5} <:PMF> pmfMul jarLike(modelState, `V) normalise
```

restrictedAtField could be statically typed - but that might be a lot of work and not a lot of gain - consider the 
cases of reading the data from a csv (best we can do is a post read assert) and even harder reading the modelState from 
a csv.

In terms of code generation and compilation it may not make sense. However, we could provide access to the type system 
for use in a program to do runtime type assertion.

To start with we should use exponentials and maybe variable length structs.

```
modelState: ({tag:`J1, (V: 30, C: 10)}, {tag:`J2, (V: 20, C: 20)})
```

```
<:cookieCount: sym**float[bmap]>
potentialWorlds: (
    {tag:`J1, cookies: {V:30, C:10} to <:cookieCount>},
    {tag:`J2, cookies: {V:20, C:20} to <:cookieCount>}
)

jarLike: {[jarStates, data:sym] <:L>
    jarStates collect {(jarState.tag, jarState.cookies[data]} to <:L>
}

{J1:0.5, J2:0.5} <:PMF> pmfMul jarLike(potentialWorlds, `V) normalise
```

if a particular implementation of `to` can handle literals then it can be run at compile time

