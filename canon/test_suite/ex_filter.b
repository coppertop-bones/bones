

// x is an agg - name, age
// _.y is collection of name contextually defined

{ x select {r `name in _.y} }

{x select [[r] r `name in _.y] }

// {select from x where name in y}

//{select(x, {[e]


// goal - be more accessible than VBA

// python list comprehension
// [r for r in x if r.name in y]


filter
select


// indexy - discourage
{x at (x `name contains y)}

// rangey - no far too complex

//explicit outputs
//where
//in


// positional outputs
// named outputs - struct / dict

(r2, m, c): data regress(,`height, `age`gender) `r2`m`c



