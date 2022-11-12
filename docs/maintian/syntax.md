

In no particular order:

Syntax is divided into groups, phrases and type-lang.



#### comments
```
// line comment
/- block / inline comment -/
```


#### literals
```
1       // literal integer
1.0     // literal decimal
"a piece of text"
`symbol
`"symbol with a space"
`a`list`of`symbols
2022.11.05  // date
0:30.001    // 30 seconds and 1 millisecond
12:30       // 12 hours and 30 minutes
12:30:01    // and 1 second
2022.11.05T19:30        // the lighting of the bonefire in some local time
2022.11.05T19:30LON     // the lighting of the bonefire in London time
```


#### snippets
```
phrase1
phrase2
```

```
phrase1. phrase2
phrase3
```

#### lists
```
(1,2,3)     // 1D
(1,2;3,4)   // 2D
```


#### assignment
```
a: 1
1 :a
```


#### group - parenthesis
```
1 * (2 + 3)
```



#### group - block
```
[[x] x + 1]                     // explicit arg x
[[x:count] x + 1]               // arg with type annotated
[[x:count] <:count> x + 1]      // return type annotated
```


#### group - function
```
{x + 1}                         // implicit arg x
{[x] x + 1}                     // explicit arg x
{[x:count] x + 1}               // arg with type annotated
{[x:count] <:count> x + 1}      // return type annotated
{{x + y}}                       // binary
```
Functions defined with single braces are unary but maybe immediately cast into nullary, binary or ternary.

```
sally: {x+y+z}<:ternary>
sally: {a+b+c+d}<:ternary>
```



#### application (calling a function)
```
fred()
fred(1)
fred(1,2)
fred(,2)
fred(1,)
1 fred                          // unary style
1 joe 2                         // binary style
1 sally 2 3                     // ternary style
1 sally(,,,4) 2 3               // mixed partial fortran and ternary style
```
Restriction - in order to keep the peace, a name for a function may only have one immutable style, e.g. if we define
`to` to be binary in one place it can only be binary in every other place. Conflicts are raised during parsing.



#### group - frame
```
([] name1:col1/type1, name2:col2/type2...)      // unkeyed frames
([name1:col1/type1] name2:col2/type2...)        // keyed frames
```



#### precedence within phrases

groups have precedence over phrases and within a phrase fortran style application happens before pipeline style and 
otherwise everything is strictly left to right.


#### type-lang

type-lang can occur in two contexts - in a type-lang group `<:...>` and after a function / block parameter.

```
<:Pokestyle:>                           // ensure an atom named Pokestyle exists
<:Pokestyle>                            // refers to the type named Pokestyle
<:Electric: Pokestyle & _Electric>      // create a new named type Electric - the intersection of Pokestyle and _Electric
```

```
A+B                                     // union of A and B
A&B                                     // intersection of A and B
A*B                                     // tuple, i.e. (A, B)
()                                      // null tuple
{fx:num,name:txt}                       // struct with fx as a number and name as a piece of text
N**num                                  // a list of numbers
txt**num                                // a dictionary that maps a piece of text to a number
num*num^num                             // a function that takes two numbers and answer a number
A*B[err]                                // low precedence intersection
```


casting / coercion - the class of a value may not be changed

```
"hello" <:txt&greeting>                 // casts the literal text to txt&greeting
"hello" <:+greeting>                    // adds greeting (intersects) to the literal text
"hello" <:txt&greeting> <:-greeting>    // removes greeting
```

precedence is &, +, *, **, ^, []

uninhabited intersections cause a type error




