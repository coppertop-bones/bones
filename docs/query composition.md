
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

frame by_ `a`b gather(, (`a`b, sum, {fab:{x`a + x`b}}))

frame by_ `a`b pivot(, (sum, mean))                     // col `b as titles
frame by_ `a`b pivot(, `c, (sum, mean))                 // col `c as titles
frame by_ `a`b pivot(, frame by `c`d, (sum, mean))      // cols `c`d as titles

frame where {x: x`a < 1}
frame by_ `a`b where ({x`a < 1}, {x`b == `fred}, {x count > 5})
frame by_ `a`b where {(x`a < 1) and (x`b == `fred) and (x count > 5)}

frame1 lj (frame2 by_ `idCol)
```

is ```x `a``` the same as ```x.a``` - do we reserve x.a just for names?

x.a: 1
x`a`b:1
x `a `b:1
x`a:1
x`"impl vol": 0.05
x."impl vol": 0.15

product access - x.a,  x."imp vol" and x.1

exponential access - x`a,  x`"imp vol", x[1], x name, x[name]

so `a`b is an exponential not a tuple

gather and pivot are unary
by, where, lj, hj, uj are binary

