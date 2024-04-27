

outine

binding types - global scope?
    defined once
    aliased once - e.g. 

```
from dm.types import dm.matrix
<:matrix: dm.matrix>
```


binding functions - module scope
    may be extended (i.e. overloaded)

binding values - local scope with additions
    may be rebound
    immutatbility
    CoW
    auto rebinding (like q)
    returning one value is restrictive
        restrict normal scope to just local variables (like q)
        add non-local scope accessing


# binding types


# binding functions


# binding values
In bones we say a name is bound to a value. E.g. the name `a` can be bound to a list.

We define a mutation as the alteration of something referred to by one name that affects the contents referred to by 
another name. Since we prevent mutation by default binding implies copying in our conceptual model. E.g. if `a` is 
bound to a list and `b` is bound to the thing in `a` we get:

```
a: (1,)
b: a
a append 2
(a == (1, 2)) and (b == (1,))
```

(Under the hood we employ a copy-on-write mechanism to reduce the amount of copying).

We detect if a change is made within the contents of the value a name is bound to, e.g.

```
a: (1,)
b: a
a[1]: 2
(a == (2,)) and (b == (1,))
```

This choice of syntax, i.e. using the style of update common in languages that mutate, is borrowed from q and chosen to
avoid the style, often seen in functional languages, where an update has to be written as an expression with one 
output. E.g.

```
a: (1,)
b: a
a: a at: 1 put: 2
(a == (2,)) and (b == (1,))
```

This doesn't look too bad but when we need to go deeper things get messy:

```
a: ((1,2), (3,4))
b: a
a: a at: 1 put: ((a at 1) at: 1 put: 2)
(a == ((2,2), (3,4)) and (b == ((1,2), (3,4)))
```


We can see from the above alternatives to the syntax of returning one value from an expression that it is moot. We
also other ways to return multiple values whilst keeping code clear, expressive, immutable and type checked.

Consider, the following:

```
fred: {
    a: 1
    incA()
    a == 2
}
incA: {a: a + 1}
```

In incA is `a` referred to before assignment?
In fred and incA is `a` the same name?

We cannot tell.


In C we would have to declare a static variable `a`, instead in bones we restrict the default scope to local, i.e. 
regular value names cannot refer to parent function nor module scope, and add out of local scope access, thus:

- _..<name> for global access
- _.<name> for contextual access
- ..<name> for module access
- .<name> for parent access

### using global scope
```
fred: {
    _..a: 1
    incA()
    _..a == 2
}
incA: {_..a: _..a + 1}
```

I.e. `_..a` is a global


### using local and parent scope
```
fred: {
    addOneToA: {.a + 1}
    a: 1
    a: addOneToA()
    a == 2
}
```


### using module and local scope
```
a: 1
fred: {
    addOneToA: {..a + 1}
    a: addOneToA()
    a == 2
}
```

### using contextual scope
```
fred: {
    _.a: 1
    addOneToA: {_.a: _.a + 1}
    addOneToA()
    _.a == 2
}
```



## Names

For a function scope A we have five sorts of names and we track if those names refer to types, functions or values.


functions inherit from their parent scope up to module

local functions
- style `fred`


values do not inherit
local, global and contextual values can be rebound from scope A, parent and module cannot be rebound from scope A

local values
- style `fred`

parent values
- style `.fred`

module values
- style `..fred`

contextual values
- style `_.fred`



## multiple outputs

For typing it is important to 


side effects are over stated and conceptually unclear


type names are assign once
function names maybe extended (i.e. overloaded)
value names may be rebound











## TO SORT

Material I've read from the Julia community present it as if it simply solves the expression problem.


The goal is to define a datatype by cases, where one can add new cases to the datatype and new functions over 
the datatype, without recompiling existing code, and while retaining static type safety (e.g., no casts).


The extensibility problem




consider a module std.ppall

```
load core
from core import PP

ppAll: {xs do: [[x] x PP]}
```
ppAll <:(N**T)*stdout^stdout>
PP <:T*stdout^stdout>

if we write:

PP: {[x:i32] print(stdout, x)}
PP: <:i32*stdout^stdout>

who has access to PP?
how do they find PP? a global namespace?
how do we control what they see? can every one see PP: <:i32*stdout^stdout> or just who we explicitly say


if ppAll is imported its definition says it can be extended to handle f64 since it's a templated / generic function


but if we do:

load std.ppall
load verbose.pp
load terse.pp

we want to have a shortcut way to customise lots of the program - e.g. use verbose.pp or terse.pp - contextual or 
dynamic scope would be needed

ppAll should be compiled and immutable

thus the exact version of PP must be captured in the type of ppAll

so we have ppAll with the context of verbose.pp and ppAll with the context of terse.pp

i.e. we should do something like


```
load core
from _ import PP into ..

ppAll: {xs do: [[x] x PP]}
```

to call it

```
load std.ppall
load verbose.pp
load terse.pp
from fred.ppall import ppAll


ppVerbose: {
    from verbose.pp import ... into _
    xs ppAll
}
(1,2,3) ppVerbose


ppTerse: {
    from terse.pp import ... into _
    xs ppAll
}
(1,2,3) ppTerse
```



aside

{stdout take -3 == 'C:>'}

has stdout as an input but not as an output

{_..stdout: _..stdout put 'hello'}

has stdout as an input and as an output



by default in Python the bones namespace matches the python one


```
from verbose.pp import PP

@coppertop
def PPEach(xs:N**T):
    for x in xs:
        x >> PP
```


```
from verbose.pp import PP, fred

injectInto([PP, fred], '')
```


adds sally to this module, the root and fred

from _.dm.blar import *         # imports from the bones namespace

import _.dm.blar            # do we ever need this form?


in python _ is used as a TBC arg, the contextual scope and the shared python-bones namespace / module


```
INJECT_INTO = ''

@coppertop(injectInto='fred')
def sally():
```

```
BONES_NS = ''

@coppertop(bns='fred')
def sally():
```


the overload in the python module could be different the bones one into the equivalent module

we want to be able to decorate local functions and use them in the same module



```
from _ import PP

@coppertop
def PPEach(xs:N**T):
    for x in xs:
        x >> PP
```





in bones PPEach is a templated / generic function so when called the compiler will have to figure PP

if PP is not global how can the compiler find the implementation?

    is we have a big bag of overloads then how do we protect?

the PPEach has to be compiled in the context of the extended PP


importing pulling into vs pushing into AND we have a lot of functions to manage

map is generic

```
map: {[xs:(N**T1), fn:(T1^T2)] <:N**T2>...}
```

ppAll is templated

```
ppAll: {[xs:N**T1] <:null> xs do: [[x] x PP].}
```

Q1 how do we know PP should be extensible? A1 inference means x -> T1 
Q2 where do we go to to get PP. A2: the import and if the import doesn't import an extensible version of PP at some 
point e.g. [1, myNewType]  ppAll will not compile. So in bones we need to import PP from an extensible module

In bones with doesn't cause recomiplation only compilation of newly needed concrete implementation.

from _ import PP

injecting into is more mutative than rebinding but since nothing gets recompiled we are somewhat safe


function definitions in a bones module a.b should impact the python module a.b and vice versa - i.e. they share the 
same mf?

this is monkey patching and a potential headache to debug - consider

from a.b import fred as fred1
run bones that defines a new overload for fred
from a.b import fred a s fred2

fred 1 != fred2 - nasty sort of mutation

so either python or bones can create a module but neither can mutate it


we want to reuse the name raad, csv.read, xlsx.read and so on
from import csv.read

so an overload is not a thing??

in bones an overload is a set of functions than the compiler has figured could be called

in python an overload is the set of all functions that share the same name an number of arguments

do we ever need the local overloads in python?

can we just share one mutating mf?




