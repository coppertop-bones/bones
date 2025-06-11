## BONES

Bones is a scalable, minimalist (bare bones), high level domain specific scripting language (designed for people 
ages 8 - 80+) for data wrangling and algorithm development combining the pithiness of kdb/q and the readability 
of Smalltalk with multiple-dispatch, partial functions and type inference.

This repo contains a Python implementation of the parts of the bones langauge - i.e. although working, it is not 
finished yet. The documents here are intended for programmers wishing to understand the bones implementation.

For documentation for how to use bones - see https://github.com/coppertop-bones/docs.

To install the python version of bones

```
pip install bones-lang
```

<br>

Fundamental values

Bones should help us faithfully represent our ideas so we can use the computer for tasks we can't do in our heads.

- it should point out mistakes in our code like a word processor identifies spelling and grammatical errors
- it should be productive to express our thinking in a clear manner that can be reasoned about
- it should be accessible and discoverable
- it should be easy for programmers to help people

And, almost most importantly, it should be fun to do so and result in pleasing and elegant code.

<br>

Implementing the fundamental values

The language is designed and implemented such that:

- Values are assumed to be immutable
- Effects are captured in the type system
- Name scopes are controlled in a way suitable for typing yet that feels flexible
- Strong typing helps identify bugs
- Some weakness from source code (where the user lives) to first function call can ease the type burden safely
- Subtyping helps constrain and compartmentalise behaviour into understandable chunks
- Polymorphism and overloading help reduce conceptual and syntactic clutter and reuse ideas
- Type annotations are only necessary when the user wants to express a subtlety thus reducing clutter
- The programmer should have no anxiety that any performance issues can't be addressed, often with ease
- Pipeline style is the principal syntax of composition and enhancing expressivity

<br>


### SYNTAX OVERVIEW FOR PROGRAMMERS

As a semantically functional bare bones domain specific langauge (DSL), bones just provides the machinery of type 
inference plus some organising symbols - everything else (including conditionals, loops, exponential order data 
structures, etc) is provided by external libraries. It also presents a slightly restricted 
programming model that is value (as in Plain Old Data) only and single threaded with automatic memory management. It 
is not a general purpose language (GPL).

Within the organising structure, the building blocks of a bones programs are phrases. Phrases comprise verbs, 
and nouns (identified by a name) and literals. 

Literals include 1D and 2D tuples, structs, values (i.e. integer, decimal, string, bool, symbol, dates and times), 
panels (aka tables), function definitions, blocks (deferred evaluation tuples), type descriptions and assignments. 
Verbs and nouns are identified by a name. Many literals can contain phrases. A sequence of phrases is termed a snippet.

Python functions decorated with @coppertop may be directly loaded into the kernel via the load statement. Symbols 
from other modules (including any loaded from Python) may be made available via the import statement.

As well as the common unary style piping, e.g F#'s |> operator, R's magrittr package, and q/kdb and Smalltalk's 
space separation syntax, bones allows right association in a pipeline (e.g. similar to single argument forms of ~, -, 
+ and ! common in many languages), and binary and ternary infix styles. Each name or symbol is globally agreed to have 
exactly one (unchanging) pipeline style - these are termed nullary, unary, binary, ternary and rau 
(for right-associative-unary).

Function application with parentheses has precedence over the other styles and a bones phrase basically reads 
left to right with no precedence distinguished for symbols. This makes pipelines easier to parse at the expense of
not supporting Junior-school level BIDMAS / BODMAS. This is in line with q/kdb and Smalltalk and whilst means the 
occasional upset with *, / and ^ means that parentheses are used for clarity rather than because a complex precedence 
scheme has unintended consequences on code readability - particularly in the reading and writing of pipeline 
style. The BIDMAS / BODMAS decision may be revisited but the usual (and complex) precedence rules are so disruptive 
to pipeline style that it seems impossible to incorporate them. (The upside of left-to-right only precedence is that the 
parser is much simpler).



### SYNTAX TOUR

#### comments

```
// a comment
```

<br>

#### separators
Almost everything in bones is a phrase. (A phrase is almost an expression but not quite as they don't have to return 
a value to the location they are written). Phases are separated either by full-stops, or by new-lines with no 
following additional indentation.

```
(1,2,3) do print. (4,5,6) do print      // two expressions separated by .
1 + 1. 2+2
```

```
(1,2,3) do print                        // separated by a new line and no indentation
(4,5,6) do print
```

```
(1,2,3)                                 // a new line but next line is indented
    do print
(4,5,6)                                 // now we have a new expression
    do                                  // print has not collaspes the indentation so continue
    print
(7,8,9) do                              // (7,8.. terminates the indentation run
    print
```

<br>

#### some literals

```
1                       - a literal integer
1.0                     - a literal decimal
2000.01.01
16:15
"hello"
`fred                   - a symbol
`fred`joe`sally         - a list of symbols
(1,2,3)                 - a tuple of literal integers
(1,0,0;0,1,0;0,0,1)     - a 2 dimensional tuple of literal integers
```

<br>

#### function calls
```
aConstantValue()
join("Hello ", "world!")
```

#### pipe style

A phrase is interpreted left to right except for function application which has precedence over the pipeline.

```
1 addOne
1 add 2
1 + 2
(1,2,3) do print
(1,2,3) both add (1,2,3)
expr ifTrue: "yes" ifFalse: "no"
(1 + 2) * 3
("a", "b", "c") (3, 2, 1)
```


<br>

#### ordinals
index, offset, excel, roman \
Default ordinal (i.e. how a literal int is interpreted) is the index rather than the offset

<br>

#### functions
```
{[a] a + 1}
{x + 1}
```

<br>

#### assignments
```
addOne: {x + 1}
{x join "One"} :addOne
pad`Re[player].state.1: YES         // product access, exponential access
a, b: (1,2)
```

<br>

#### names
values may be named a-z, A-Z, 0-9 and _ \
functions may be named with the same rules or alternatively by using +-=!@£$%^&*|\\/~?#<> \
()[]{}"`.,; are reserved by bones \
Some sequences are also reserved, i.e. //, <:..>, {...}, {[...]...}, ([...]...)

<br>

### type tags
```
1 <:offset>
{[x:num] x + 1}<:num> :addOne
```

<br>

#### including other code
```
load bones.std                          // loads a module into the kernel
from bones.std import do, print         // adds the name do and print to this module's scope
```

<br>

#### scopes
```
.aReadOnlyVariableFromMyParentsContext
..aReadOnlyVariableFromMyModulesContext
_.aRWVariableInTheContextualContext
_..aRWVariableInTheGlobalContext
```

### Next

#### example bones code working end to end

For a suite of example .bones files:

* lex -> tokens
* group -> token groups + some markup
* parse -> untyped / partially typed TC (Tree Code aka AST)
* infer and check types -> typed TC (fully concrete and type schema variables)
* build & bind (rebind affected concrete TC) -> concrete TC
* at this point a snippet will be runnable (assuming no type errors) - snippets are run on import and REPL / jupyter execution
* functions in the kernel can be called from python via something like `x = kernel.module.fn(a,b,c)`


#### determine how to do exception handling

We can easily add a trap function that converts a signal into a error value however we want to be pluralistic with 
implementation languages so may need a better sense of signal trapping at the TC or (hopefully not) langauge level.
In the sorts of use cases that bones is intended for typically errors can be modelled as data and although one can 
imagine that a far reaching escape (e.g. the ^ borrowed from Smalltalk) from the current path (e.g. over several 
functions) could be useful it is not clear that there isn't an elegant alternative.


#### collaborative / community developent / selection of a bones.std

Currently dm.core contains bits and pieces of library style code but Jeff Atwood's [The Delusion of Reuse and the Rule of Three](https://blog.codinghorror.com/the-delusion-of-reuse/) 
(also [Rule Of Three](https://blog.codinghorror.com/rule-of-three/))
implies that more than one common / standard library will emerge for bones and that it will arise from a 
joint focus and application into multiple use cases. Needless to say any bones.std should be as integrated and well 
designed as Smalltalk-80's / VisualWorks.


#### error messages

In the tradition of Mr Kipling, these should be exceedingly good. Grouping helps. ErrSite should help. They should be 
built into the analysis process too. The goal is that the error message should be enough for the user to 
instantly know how to fix the problem and not to have to hunt around to understand the message.

<br>


### Later

#### profiling

There's a popular quote about premature optimisation. The deeper question is why do people favour fast 
code over clear code (assuming they can write well and are not in a rush) when the code in question is not on the 
critical path? A couple of answers come to mind - the thrill of speed and a generalised anxiety of not being fast 
enough. To help bones programmers avoid this trap, we should have first class profiling - aggregated time within a 
scope as well as stopwatch style end to end aggregated time. I'm with Paul Graham on this one. Count based profiling 
should be pretty easy to implement.

#### compile

Convert TC to Byte Code (BC), Internal Representation (IR) for a compiler (e.g. [MIR](https://github.com/vnmakarov/mir/)
or possibly QBE, LLVM, etc) and / or Machine Code (MC).

#### duck types
e.g. N**T1{PP(T1)->str} - a seq of types that have pretty print (PP) defined \
e.g. N**T1{area(T1)-cm2} - a seq of types that have the function area defined


#### ABIs

Bones will be able to call C ABI functions and should be able to call Fortran functions.


### contingent types
the intention is to only dynamically check these - if we ever (unlikely) need pattern matching they would be used there \
e.g. N**T1{fred&joe} - a seq of types that the predicates fred and joe return true



GOALS

1) pybones - a python implementation of bones where the standard library is implemented in python, where python can
   call bones and bones call python
