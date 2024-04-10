# BONES

Whilst this cheatsheet completely covers the essential features of the bones language refer to other documentation 
whenever a fuller explanation is required.


## PURPOSE

Bones is a high level, high performance, decision support language intended for non-career programmers aged 8 to 88. 


## PITHY SUMMARY

bones is intended to make the structure of what is going on more explicit and simpler to follow but in a textual form
rather than a GUI form - hence the language is as simple as we can make it ("bones" is short for "bare bones language")
and much of the useful stuff (including control flow) is put into libraries.

we have functions, blocks, types, ability to (partially or fully) call functions and blocks, names, the ability to
bind names, and scopes to organise the names - obviously we also need to be able to load preexisting work and import
names, as well as the usual literals. but that's the essence - semantically we default to immutable values (but can do
agents), function names may form a union / intersection (depending on your view point) of functions that are
automatically selected on context (aka multiple dispatch), and functions and blocks are first class although blocks are
restricted to being stack based - to reduce spaghetti we provide early return, signals (aka exceptions) and auto
rebinding of lvalues - finally we add some convenience - the piping and hole based function argument syntax and
implicitly passing parent names as arguments to local in scope functions.

under the hood we do the memory management for the user, infer principle types, provide a single threaded programming
model, use the C-ABI and generate code for consumption by optimising compiler backends, e.g. QBE, MIR, LLVM, etc.

tooling wise - we have AST and bytecode interpreters and debuggers with profiling support.

bones can call and be called by Python and C.


## CONCEPTS

A central idea of bones is that it does all sorts of things for you so you don't have to, and thus can instead focus 
on solving the problem at hand.

### SIMPLE MINIMAL / BARE-BONES SYNTAX
Bones' syntax, based on Smalltalk - which happens to be designed with children in mind - tends to fade into the 
background leaving you to be able to mainly reason about the data and functionality, giving a more problem focussed 
experience.

### VALUES
We treat structures in memory as if they were values, i.e. cannot be changed. Modeling data in memory in this manner
means you don't have to worry about aliasing. This also means you can't build cycles, so programming problems tend to 
evolve in a simpler direction.

### FUNCTIONS
First class, anonymous functions with partial binding to support composability.

### BLOCKS
Lighter weight than functions. Since blocks share the enclosing parent's names and we allow names to be rebound 
they allow "imperative" style syntax whilst keeping the benefits of immutable semantics.

### NO CONTROL STRUCTURES
Like Smalltalk, control structures (i.e. if-else, switch, for, while etc) are not provided in the language but instead
libraries provide higher order functions for this purpose. Blocks make this efficient. Experience with Smalltalk shows 
this opens the way to more extensible systems.

### OVER-LOADING / MULTI-DISPATCH
Less function names to remember. Overloads tend to lead to / can be used to create intuitive apis. Patterns tend to 
become more enculturated in overloaded languages.

### AUTOMATIC MEMORY MANAGEMENT
Supports composability and efficiency. Fast bump allocation and nursery reuse improves mutator locality compared to 
other allocation styles. Don't have to think about it.

### COPY-ON-WRITE
Values are copied only when necessary, i.e. under the hood they are shared between names. Destructive update is
used when storage is not shared. The ref-counting mechanism that implements this is also used as a memory management 
optimisation.

### SYSTEM FRIENDLY
Physical memory is aggressively returned to OS.

### SINGLE THREADED CONTROL FLOW MODEL
Under the hood multiple threads may be used but the language flow is presented to the user as a single thread.

### AGENTS
Ability to write non-value-based code when necessary. However, due to the target problem domain, this is much less 
useful than might be initially thought.

### INTEROPERABILITY
C-ABI, pinning, Python, Itanium exceptions, etc. Functions use the platform's C ABI and the itanium exception ABI. 
Bones may call or be called from any language that supports the C-ABI. Structures are laid out C style in memory.
Bones can easily be called from and call Python.

### SIMPLE TYPE SYSTEM WITH EXPLICIT SUBTYPE RELATIONSHIPS
The type system is formed around the needs of multiple-dispatch and models subtype relationships explicitly including
problem domain typing. For example, it is possible to prevent adding amounts in two different currencies. 

### STRONG STATIC TYPING
Better and earlier detection of many types of error. Also paves the way for more optimisation.

### PARTIAL TYPING
Code will run as long as at least one happy path exists. One can start with exploratory programming style with a 
minimal program, but with the confidence that the same code can easily be improved to production quality code, by 
completing additional cases and adding annotations as necessary.

### TYPE INFERENCE
The type system also happens to be algebraic in nature meaning it is quite amenable to inference, yielding principal 
subtypes. This also improves programmer productivity as annotations are more about documentation and refinement and not 
required upfront.

### ERRORS
Signalling mechanism interrupts flow. Signals can be trapped and handled. Don't have to think about every eventuality 
before running.

### PROFILING
Build in so you know early on if you need to architect for performance up front or if can be fixed later if necessary.


## SYNTAX

### RESERVED PATTERNS
```
[...]               - blocks and exponential accessing
[[...]...]          - blocks with parameters
{...}               - function (unary) and literal structs
{[...]...}          - function with arguments
{{...}}             - function (binary)
{{[...]...}}        - function (binary) with arguments
(...)               - parenthesis, literal tuples, function application 
<:...>              - type-lang
.                   - tuple / struct accessing (including namespaces), phrase separation, 
                      accessing parent scope (as an implicit parameter)
..                  - accessing module scope
_.                  - accessing contextual scope
_..                 - accessing global scope
:                   - binding, separation of parameter names and types
,                   - phrase separation
;                   - phrase separation
\                   - line continuation??
^                   - block / function exit
^^                  - block / function exit
^^^                 - block / function exit
!!                  - signalling
load ...            - load a module
from ... import ... - import names into a module namespace
...                 - elipsis
```


### NAMES
- value names - _, A-Z, a-z and 0-9 - must start with either a letter or _ 
- function / block names - _, A-Z, a-z, 0-9, <, >, !, =, #, @, $, %, ^, &, *, +, /, -, |, ~, ' and ? - may not start 
  with a number nor a * \
- agent names - start with a * followed by _, A-Z, a-z and 0-9

Function names can be interspersed with :, for example ifTrue:ifFalse:, which can be used with a Smalltalk style 
pipeline. 


### PHRASES

A phrase is left to right sequence of literals (values, functions and blocks), names and calls that returns a value. 
Given:
```
n0, n1, n2, n2      - four nullary functions with 0, 1, 2 and 3 arguments
u1, u2, u3          - three unary functions
b2, b3              - two binary functions
t3, t4              - two ternary functions
```

fortran style function invocation:
```
n0()
n1(n2(1,2))
```
and similarly for the unary, binary and ternary functions.

partial invocation:
```
u3(,2,)(1,3)        - in total the same as u3(1,2,3)
```

unary pipeline:
```
1 u1                - u1(1)
1 u2(,2)            - u2(1,2)
2 u2(1,)            - u2(1,2)
3 u3(1,2,)          - u3(1,2,3)
1 u1 u2(,2)         - u2(u1(1),2)
```

binary pipeline:
```
1 b2 2              - b2(1,2)
1 b3(,2,) 3         - b3(1,2,3)
2 b3(1,,) 3         - b3(1,2,3)
1 b2 2 b3(,3,4)     - b3(b2(1,2),3,4)
```

ternary pipeline:
```
1 t3 2 3            - t3(1,2,3)
1 t4(,2,,) 3 4      - t4(1,2,3,4)
```

keyword style: \
given a 3 argument function ifTrue:ifFalse:
```
condition ifTrue: thing1 ifFalse: thing2  - ifTrue:ifFalse:(condition, thing1, thing2)
```

so putting it all together 
```
a + b addOne
```


### BINDING
We say that we bind a name to a value, i.e. we give a value a name. We may rebind the name to a new value.

Bind the name(s) on the left to the thing(s) on the right. There must be no space between the name(s) on the left and 
the :, and there must be a space between the : and the phrase on the right.
```
a: 1                    // binds the literal number 1 to a
(a, b): (1, {{x + y}})  // binds the literal number 1 to a and the binary function to b
atup: (1, {{x + y}})    // binds the tuple (1, {{x + y}}) to atup
(a,b): atup             // unpacks the tuple atup and binds the literal number 1 to a and the binary function to b
```

Bind the name(s) on the right to the thing(s) on the left. There must be a space between the phrase on the left and 
the :, and there must be no space between the : and the name(s) on the right.
```
"hello", `there :(a,b)  // binds the text "hello" to a and the symbol `there to b
```

Conceptual, if we imagine that the storage for a value is a matchbox, then a name is bound to a matchbox that contains 
a value and rebinding the name means referring to a different matchbox that contains another value, rather than 
replacing the value stored in the matchbox. Under the hood this is done efficiently but in such a way that the 
conceptual is not violated.

A agent name is also bound to the matchbox but we may change the contents of the matchbox, mutate the value. 


### SCOPES
In bones, we have global scope (which could be backed by disk similarly to q/kdb), module scope, contextual scope and
local scope. Functions create their own local scope. Blocks also create their own local scope but also share the scope 
of their parents and can rebind parents' names. New names are only visible in the block's scope and not to any parent.

Child functions may see but not rebind a parents function-names though can extend them by overloading. Child functions 
may not see parents' value / agent names, though it is easy to implicitly add a direct parent's value / agent name as 
a parameter.

This scoping style means we don't have closures and don't seem to need monads, thus simplifying the language for the
intended target audience.

Contextual scope is like a contextually defined / changable global scope. To be discussed later.


### FUNCTIONS
A function defines some code that we may run explicitly at a later point. It can have inputs and outputs. A function 
creates a new scope that cannot see value or agent names in parent scopes, but can see function names.

Examples of binary functions to add to two 64-bit floating point numbers:
```
1.0 {[x:f64, y:f64] <:f64> ^x + y} <:binary> 2.0
1.0 {[x:f64, y:f64] ^ x + y} <:binary> 2.0          // rely on type inference
1.0 {[x:f64, y:f64] x + y} <:binary> 2.0            // last phrase is return value
1.0 {[x, y] x + y} <:binary> 2.0                    // reply even more on inference
1.0 {{[x, y] x + y}} 2.0                            // use {{...}} form for binaries
1.0 {{x + y}} 2.0                                   // use implicit arguments
```


### BLOCKS
Similarly, a block also defines some code that we may run explicitly at a later point. They create a new scope, but 
since the can see the parents' scopes it only needs to contain locally defined variables that do not appear in the 
parents' scopes.

Examples of blocks to add to two 64-bit floating point numbers:
```
[[x:f64, y:f64] <:f64> x + y](1.0, 2.0)     // blocks can only be called fortran style and ^ exits the direct parent
[[x:f64, y:f64] x + y](1.0, 2.0)            // rely on type inference
[[x, y] x + y](1.0, 2.0)                    // reply even more on inference
[[x] x + y](1.0)                            // refer to y defined in the parent scope
```


### TYPE-LANG
Type-lang is the name given to the mini-language that describes bones types. In bones it occurs in three places, in a 
`<:type-lang>` type annotation used to indicate the type of a name and to the right of a name after a `:` in a struct 
or function / block parameter definition. Type-lang used in struct / function / block definition may only be a single 
expression and may not define new nominal types.

```
u32: nom                // nominal name "u32"

u32 + err               // unnamed union
txt & isin              // unnamed intersection

ccy: exclusion          // exclusion type named "ccy"
GBP: ccy & GBP          // intersection type named "GBP" with a recursive definition that doesn't need predeclaring

nonconst: recursive     // we are about to make a recursive definition so predeclare nonconst
const: not nonconst     // const is not nonconst (whatever nonconst is, which we don't know at this moment)
nonconst: implicit, const & nonconst 
                        // nonconst is implicit and is the intersection of const and itself, i.e. is a subtype of const
                        // thus char * (i.e. N**char) can be passed to a function expecting char const * (i.e. N**const&char)

u32*u32                 // unnamed tuple of two unsigned integers
point: {x:f64, y:f64}   // structure named "point"
N**u32                  // sequence of unsigned integers
u32*u32 ** f64          // map with (u32,u32) as keys and f64 as values
u32*u32 ^ f64           // function or block with (u32,u32) as arguments and f64 as return type

LHS - RHS               // the union or intersection on the left less the type on the right, e.g. (u32 + err) - err would be u32

u32[GBP]                // intersection with lower precedence

PRECEDENCE - (parentheses) then  & then + then * then ** then ^ then []


T1...T20, TA...TT       // schema variable T1 etc
N1...N20, NA...NT       // index1 etc, a convenience to indicate corresponding sizes, e.g.
                        // (NA**NB**f64) * (NB**NC**f64) ^ (NA**NC**f64) for matrix multiplication
O1...O20, OA...OT       // offset1 etc
```



### COMMENTS
```
// rest of line is a comment
/- block comment -/
/! conditional comment, e.g. for optional inclusion of code !/ 
'{[...] ...}' - breakouts for embedding other languages
```


### LITERALS - strings, symbols, numbers, datetimes, tuples, structs, tables
"fred"                  - string
`fred and `fred`joe     - symbol and symbol list
([a:u32, b:txt] a: (1,2), b: ("one","two"))



## SEMANTICS

### INDEXS AND OFFSETS
Indexes, such as page numbers, final positions on the starting grid, etc, start at one. Offsets start at zero.


### IMMUTABLE VALUES
Like q/kdb values in bones may not be mutated or changed. Conceptually a change to a value is the creation of new value 
with the desired changes incorporated. Thus, it is impossible to make a change to a value structure via one name that 
can be seen by another name. This allows us to provide nice syntax for deep change, for example:

```
a: {v: (1,2,3)}
b: a
b.v.1: 3.  b.v.3: 1
a == {v: (1,2,3)}
b == {v: (3,2,1)}
```

This also means it is not possible in the bones language to create recursive value structures.


### AUTOMATIC MEMORY MANAGEMENT
Memory management is handled on behalf of the user using a combination of stack, arena and region style - conservative
on stack and precise on heap. By default, objects may be moved by the memory manager but may be pinned when desired, 
for example when needing to interface with external code.


### SIGNALS
The kernal may be signalled, and will search up the call stack until a signal trap is found which is then invoked to
determine what next to do - close resources, resume, panic, ask the user (e.g. "this is taking a long time, abort?"), 
and so on. Under the hood we will likely use the itanium exception mechanism.



## METATYPES

TBC

intersections... because there are types that cannot be inferred that remove whole classes of bugs



## OTHER FEATURES

The accessing functions, '.' for product types, and '[...]' for non-function exponential types may be overloaded by 
libraries and / or users.

Bones can be interpreted or compiled to machine code by an optimising backend compiler such as LLVM, MIR, QBE, etc.

The bones kernel exposes function selection.



## BONES PROGRAMMING MODEL


### ON AGENTS

This is quite nice - https://www.cs.rpi.edu/academics/courses/fall00/ai/scheme/reference/schintro-v14/schintro_72.html

In mathematics a variable allows us to use something in different contexts with different values. It does not mean 
the "variable" can vary. For example the solution to y = ax² + bx + c is x = (-b ± √(b²-4ac)) / 2a but this solution is
really a template for using in different problems but in each problem whilst the "variables" are unknown they are 
constant and don't vary.

Instead of the word "variable", in bones we use the term "name". Conceptually, we say name is "bound" to a value, a 
function, a block or an agent.

When writing code it would often be very clumsy if we insisted that names were a unique set of alpha-numeric characters, 
so instead we allow names to be rebound. This is a conceptually different view on the world than the agent approach, 
which allows the agent's state to vary. Allowing rebinding opens the way to syntactically simpler but nonetheless 
immutable code, for example:

```
addOneToEach: {[xs: N**u32] <:N**u32>
    xs forI: [[i]
        xs[i]: xs[i] + 1        // xs is rebound here (maybe via destructive update)
    ]
    xs      
}

forI: {[xs, block]
    n: xs count
    i: 1
    [i <= n] whileTrue: [
        block with: i
        i: i + 1
    ]
    // n is the only useful thing we can possibly return - we cannot guarentee that xs here refers to the same value as the callers xs
    n
}

(1,2,3) addOneToEach == (2,3,4)
```

Which could be done with recursion (although not so reliably with a C-ABI):
```
timesDo: {[count, aBlock]
    count > 0 ifTrue: [count - 1 timesDo: aBlock()]
}

i = 0
2 timesDo: [i + 1]
```

Every function in bones is pure - i.e. all the inputs and outputs are well-defined even though sometimes those inputs / 
outputs might be hard or almost impossible even to replicate - such examples including streams such as stdin and stdout.

In bones, under the hood we change memory and register for efficiency but without breaking the above model.

Our assertion is that agents introduce dependencies into a program that are unnecessary for decision-making, however, 
sometimes we may want to go beyond decision-making, e.g. writing a compiler, or need to improve performance because 
maintaining immutability is slowing down an algo, yield curve calibration.

An agent is also a structure in memory, not essentially different to a value, that may be mutated. Thus cycles may be 
introduced. Our GC should be able to handle agents but it may be slower to manage agents memory than value memory.

Agent names in bones start with * (as it nicely parallels pointer syntax in C). Agents may be passed on the stack, 
and defined in global and local scopes, but not in module and contextual scope may not refer to agents. For example:

```
*player: <:*pos: {*x:f64, *y:f64}>
updatePlayerPos: {[*player, x, y] *player.*x: x.  *player.*y: y.  *player}
```

Given the current optimisations in bones it is not yet known if agent style programming is more or less performant 
generally than value style programming - overall performance includes gc costs and as well as mutator performance. 
Our current hypothesis is that managing agent memory may be slower than managing value memory.
