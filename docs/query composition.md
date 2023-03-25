
given a frame N**T1, and a tuple of keys T2

`by` and `by_`

by: (frame & N**T1, T2&T1.keys.set) -> group & (T2&T1.keys.set * frame & N**T1)

gather:

where:

pivot: since pivot creates new columns with titles from the data it cannot be fully statically typed only some columns


e.g. frame with \`a\`b\`c\`d\`e

```
frame gather(, {x`a + x`b})

frame by_ `a`b gather

frame by_ `a`b gather(,(`a`b, sum, {fab:{x`a + x`b}}))

frame by_ `a`b pivot(,`c, sum)

frame where {x: x`a < 1}
frame by_ `a`b where ({x: x`a < 1}, {x: x`b == `fred})

frame1 lj (frame2 by_ `idCol)
```

gather and pivot are unary
by, where, lj, hj, uj are binary

