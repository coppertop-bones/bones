## bones syntax for programmers

Bones syntax is based on Smalltalk (“In contrast, the Smalltalk syntax which ObjC is based on incubated ~10 years 
at Xerox PARC in Alan Kay’s Learning Research Group, which was focused on making the computer accessible as a 
problem-solving tool for _**children and non-programmer adults**_.”) and q/kdb.


At a high level the syntax is structured as lists of phrases.

<br>

### Phrase

A _phrase-fragement_ comprises _nouns_, _verbs_, _type-exprs_ and _assignments_ \
_nouns_ are literals or the result of the preceding phrase-fragment \
_verbs_ are functions

_verbs_ may be called / applied in one of three forms:

1) mathematical `verb(…)` form, e.g. `voo(doo(1), 2)` [^1] 
2) key-word form, e.g. `noun1 ifTrue: noun2 ifFalse: noun3` a la Smalltalk [^2] - same as `ifTrue:ifFalse:(noun1, noun2, noun3)` 
3) pipeline form

Syntacially _phrase-fragments_ come in six pipeline forms:

- _noun unary_ - same as `unary(noun)`
- _noun1 binary noun2_ - same as `binary(noun1, noun2)`
- _noun1 ternary noun2 noun3_ - same as `ternary(noun1, noun2, noun3)`
- _rau noun_ - same as `rau(noun)` - where "rau" stands for right-associative-unary
- _noun noun_ - i.e. vector based, e.g. `("a","b","c") 2 == "b"` or `("a","b","c") (1,2) == ("a", "b")`
- _nullary_ - this form prevents a verb from consuming nouns from the pipeline and may only be called `nullary()`

_phrase-fragments_ are read left to right and both the human and the parser have to know the style each 
verb takes (_unary, binary, ternary, rau_ or _nullary_). It is believed that this sort of contextualisation is more human 
friendly than the usual mathematically based call / application style.

A _phrase-fragment_ returns a noun which is passed to the next phrase fragment, thus `1 fred joe sally` is:

```
1 fred  -> noun1
noun1 joe -> noun2
noun2 sally -> noun3
```

_noun3_ is the result of the whole _phrase_.

_assignments_ bind at name to the right of the assigment operator (_:name_) to the value on the left and pass the value 
though to the next part of the phrase. E.g.
```
1 :a + 1 :b
```
results in `a == 1` and `b == 2`.\
`b: 1 :a + 1` allows the name to come brefore the _:_ and is syntactic sugar for the above.

_type-exprs_, e.g. `<:type>`, may follow any noun and are used to tell bones the noun's type. Nouns may be 
cast if their underlying memory structure is identical, for example, `myLifeSaving: 100.0 <:gbp>`. If the underlying 
memory structure is not identical then a type error is flagged.


<br>

### List

**snippet** - _dot_ separated list (where _dot_ is either an actual `.` or a new line without indentation), e.g.
```
load "adding_library"
from adding_library import +
a: 1. b: 2
a + b
```

**function**
```
{[name1:type1, name2:type2] <:return type> ... }
```
where
- ... is a snippet
- types are optional - inferred staticaly if absent
- parameter names list (i.e. the `[...]` immediately following the opening `{`) is optional but if not given the 
  parameters can be only one letter long and the order they are passed in is asummed to follow Oxford Dictionary order 
  (i.e. "A" comes before "a" which comes before "b" and so on).

So for example, `{y + x}` is the same as `{[x, y] y + x}`.

**tuple** - semi-colon separated list of comma separated lists of phrase
```
( 
  1,2,3;
  4,5,6
)
```

**block** - semi-colon separated list of comma separated lists of dot separated lists of phrases
```
[
    "a", b:1 + 1. c * 2;
    "b", d:2 + 2. d * d;
    5
]
```


blocks have deferred execution but don't create a new context (aka environment) of variables and they can take 
parameters:

```
[[name1:type1, name2:type2] <:return type> ...]
```

Example putting these together:

```
((1,2,3) map: [[e] e + 1]) collect {x + 1) == (3,4,5)
```

`collect` is a binary and is the Smalltalk equivalent to `map`. Note keyword style requires extra parentheses in a 
compound phrase.


**struct** - comma-separated list of name:value pairs
```
{name1: value1, name2: value2}
```

**panel**
```
([] a: (1,2,3), b: ("one", "two", "three"))
([a: (1,2,3)] b: ("one", "two", "three"))
```

result in a panel

| a   | b       |
|-----|---------|
| 1   | "one"   |
| 2   | "two"   |
| 3   | "three" |

where the second syntax results in a panel with an index of a which can also be accessed like any other column.

**early-exit**

_^_ exits a snippet immediately (i.e. the function in which it occurs) with the result of the phrase to it's right.

_^^_ exits a snippet immediately and all callers of the function in which it occurs attempting in the process to 
  send a _signal_ (the result of the phrase to the right) to a _watcher_ (similar to the usual exception handler but 
  with slightly more flexible semantic, e.g. a signal can be used to exit without an error, and may be resumable, 
  e.g. to call a progress bar in a long running process. The watcher will often unwind the stack but may not - e.g. in
  the case of a debugger or error logger).

```
saferDivide: {
    1/x :res notNan ifTrue: [^ res]
    x == 0 ifTrue: [^^ "dividing by zero" <:+err>]
    ^^ "unhandled condition maybe inspect this?: " join (res toText)
}
```


<br>

### type-exprs (aka type-lang)

_type_ refers to a named type (most types are anonymous) \
_type1 + type2_ - constructs a union type \
_type1 & type2_ - constructs an intersection type \
_type1 * type2_ - constructs a tuple type \
_{name1:type1, name2:type2}_ - constructs a struct type \
_N**type_ constructs an ordinal, i.e. _N_, to _type_ map (discrete exponential), e.g. an array or list etc of _type_ \
_type1**type2_ constructs a _type1_ to _type2_ map (discrete exponential) \
_type1^type2_ constructs the usual function (potentially infinite exponential) _type1_ -> _type2_ \
_[]_ also constructs and intersection type but with very weak precedence

precedence is counter to normal mathematical conventions - N** then & then + then * then {} then ** then ^ then [] \
_(...)_ is used either for clarity or when the type cannot be expressed using the precedence rules

_<:name>_ is the type named _name_ \
_<::name>_ creates a new atomic type called _name_ \
_<:type-expr:name>_ names the type given by _type-expr_\
_noun <:type-expr>_ - casts noun to _type-expr_ if compatible \
_noun <:+type-expr>_ - down-casts noun by intersecting its type with _type-expr_ (if valid) \
_noun <:-type-expr>_ - up-casts noun by removing _type-expr_ from its intersection (if valid)


<br>

----

[^1]: according to https://swiftpp.github.io/ the mathematical fn(x, y, z) style comes from Fortran

[^2]: and adopted by Apple's swift
